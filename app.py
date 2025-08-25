# 自己破産書類OCR処理アプリケーション（統合版）
import streamlit as st
import os
import json
from datetime import datetime
import fitz
from PIL import Image
import io
import openai

# 環境判定とインポート
IS_PRODUCTION = os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or 'DATABASE_URL' in st.secrets

if IS_PRODUCTION:
    # 本番環境用の設定とインポート
    from config_web import *
    from database_models_postgres import *
else:
    # ローカル環境用の設定とインポート
    from config import *
    from database_models import *

from ocr_processor import *
from llm_regex_generator import *

# Streamlit Secretsから環境変数を読み込み（本番環境）
if IS_PRODUCTION and hasattr(st, 'secrets'):
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
    # OpenAI APIキーを設定
    if 'OPENAI_API_KEY' in st.secrets:
        openai.api_key = st.secrets['OPENAI_API_KEY']

# ページ設定
st.set_page_config(
    page_title="自己破産書類OCR処理システム",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'ocr_text' not in st.session_state:
    st.session_state.ocr_text = None
if 'text_elements' not in st.session_state:
    st.session_state.text_elements = None
if 'extracted_values' not in st.session_state:
    st.session_state.extracted_values = []
if 'current_patterns' not in st.session_state:
    st.session_state.current_patterns = []
if 'document_pattern' not in st.session_state:
    st.session_state.document_pattern = None

# タイトル
st.title("🏦 自己破産書類OCR処理システム")
st.markdown("財産書類のPDFから自動的に金額情報を抽出します")

# サイドバー
with st.sidebar:
    # システム状態の表示
    with st.expander("🔌 システム状態", expanded=False):
        if IS_PRODUCTION:
            st.success("✅ 本番環境（PostgreSQL）")
        else:
            st.info("💻 ローカル環境（SQLite）")
        
        # データベース接続テスト
        try:
            session = get_session()
            session.close()
            st.success("✅ データベース接続OK")
        except Exception as e:
            st.error(f"❌ データベース接続エラー: {str(e)}")

    st.header("📁 ファイルアップロード")
    
    # PDFファイルのアップロード
    uploaded_file = st.file_uploader(
        "PDFファイルを選択",
        type=['pdf'],
        help="処理したい財産書類のPDFファイルをアップロードしてください（最大10MB）"
    )
    
    # ファイルサイズチェック
    if uploaded_file and uploaded_file.size > 10 * 1024 * 1024:
        st.error("ファイルサイズが大きすぎます。最大10MBまでです。")
        uploaded_file = None
    
    # 書類カテゴリの選択
    st.header("📋 書類カテゴリ")
    selected_category = st.selectbox(
        "書類の種類を選択",
        options=["自動判別"] + DOCUMENT_CATEGORIES,
        help="書類の種類を選択してください。自動判別も可能です。"
    )
    
    # OpenAI APIキーの設定
    if IS_PRODUCTION:
        # 本番環境ではSecretsから取得
        if 'OPENAI_API_KEY' not in st.secrets:
            st.error("OpenAI APIキーが設定されていません")
    else:
        # ローカル環境では入力可能
        st.header("🔑 API設定")
        api_key = st.text_input(
            "OpenAI APIキー",
            type="password",
            value=os.getenv('OPENAI_API_KEY', ''),
            help="正規表現の生成にOpenAI APIを使用します"
        )
        if api_key:
            openai.api_key = api_key
            os.environ['OPENAI_API_KEY'] = api_key
    
    # 処理オプション
    st.header("⚙️ 処理オプション")
    use_azure = st.checkbox("Azure OCRを使用", value=True)
    save_to_db = st.checkbox("パターンをDBに保存", value=True)

# メインエリア（以下、main_app.pyと同じ内容）
if uploaded_file:
    # 一時ファイルとして保存
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf_path = os.path.join(temp_dir, f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    
    with open(temp_pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # タブを作成
    tab1, tab2, tab3, tab4 = st.tabs(["📝 OCR処理", "💰 金額抽出", "📊 結果確認", "📈 統計情報"])
    
    with tab1:
        st.header("OCR処理")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 OCR実行", type="primary", use_container_width=True):
                with st.spinner("OCRを実行中..."):
                    try:
                        # OCR実行
                        with open(temp_pdf_path, "rb") as f:
                            pdf_data = f.read()
                        
                        if use_azure:
                            st.session_state.ocr_text = perform_azure_ocr(pdf_data)
                            st.session_state.text_elements = extract_text_with_coordinates(pdf_data)
                        else:
                            st.session_state.ocr_text = perform_google_ocr(temp_pdf_path)
                        
                        st.success(f"✅ OCR完了！ {len(st.session_state.ocr_text)}文字を抽出しました。")
                        
                        # 自動的に書類カテゴリを判別
                        if selected_category == "自動判別" and save_to_db:
                            session = get_session()
                            try:
                                similar_doc, score = find_similar_document(st.session_state.ocr_text, session)
                                if similar_doc:
                                    st.info(f"📄 類似書類を発見: {similar_doc.category} (類似度: {score:.1%})")
                                    st.session_state.document_pattern = similar_doc
                            finally:
                                session.close()
                        
                    except Exception as e:
                        st.error(f"❌ OCRエラー: {str(e)}")
        
        with col2:
            # PDFプレビュー
            st.subheader("PDFプレビュー")
            try:
                doc = fitz.open(temp_pdf_path)
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                img_data = pix.tobytes()
                img = Image.open(io.BytesIO(img_data))
                st.image(img, caption="1ページ目", use_column_width=True)
                doc.close()
            except Exception as e:
                st.error(f"PDFプレビューエラー: {str(e)}")
        
        # OCR結果の表示
        if st.session_state.ocr_text:
            st.subheader("OCR結果")
            with st.expander("テキスト全文を表示", expanded=False):
                st.text_area("OCRテキスト", st.session_state.ocr_text, height=300)
    
    with tab2:
        st.header("金額抽出")
        
        if st.session_state.ocr_text:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("🔍 正規表現パターン")
                
                # 既存のパターンがある場合は表示
                if st.session_state.document_pattern:
                    st.info(f"📁 保存済みパターン: {st.session_state.document_pattern.category}")
                    st.session_state.current_patterns = st.session_state.document_pattern.get_patterns()
                
                # 正規表現の生成
                if st.button("🤖 AIで正規表現を生成", use_container_width=True):
                    if not os.getenv('OPENAI_API_KEY') and not (IS_PRODUCTION and 'OPENAI_API_KEY' in st.secrets):
                        st.error("OpenAI APIキーを設定してください")
                    else:
                        with st.spinner("正規表現を生成中..."):
                            try:
                                patterns = generate_regex_patterns(
                                    st.session_state.ocr_text,
                                    document_category=selected_category if selected_category != "自動判別" else None
                                )
                                st.session_state.current_patterns = patterns
                                st.success(f"✅ {len(patterns)}個のパターンを生成しました！")
                            except Exception as e:
                                st.error(f"生成エラー: {str(e)}")
                
                # パターンの表示と編集
                if st.session_state.current_patterns:
                    st.write("現在のパターン:")
                    edited_patterns = []
                    for i, pattern in enumerate(st.session_state.current_patterns):
                        edited_pattern = st.text_input(
                            f"パターン {i+1}",
                            value=pattern,
                            key=f"pattern_{i}"
                        )
                        edited_patterns.append(edited_pattern)
                    st.session_state.current_patterns = edited_patterns
                
                # 金額の抽出
                if st.button("💴 金額を抽出", type="primary", use_container_width=True):
                    if st.session_state.current_patterns:
                        extracted = extract_amounts_with_patterns(
                            st.session_state.ocr_text,
                            st.session_state.current_patterns
                        )
                        st.session_state.extracted_values = extracted
                        st.success(f"✅ {len(extracted)}個の金額を抽出しました！")
                    else:
                        st.warning("⚠️ 先に正規表現パターンを生成してください。")
            
            with col2:
                st.subheader("💰 抽出結果")
                
                if st.session_state.extracted_values:
                    # 抽出された金額の表示
                    for i, value in enumerate(st.session_state.extracted_values):
                        col_a, col_b = st.columns([2, 1])
                        with col_a:
                            st.text_input(
                                f"金額 {i+1}",
                                value=f"¥{value['normalized']:,}",
                                key=f"amount_{i}",
                                disabled=True
                            )
                        with col_b:
                            st.caption(f"元: {value['raw']}")
                    
                    # 修正が必要な場合
                    st.markdown("---")
                    st.subheader("📝 手動修正")
                    
                    missing_value = st.text_input(
                        "抽出できなかった金額を入力",
                        placeholder="例: 1,234,567",
                        help="抽出できなかった金額がある場合は入力してください"
                    )
                    
                    if missing_value and st.button("🔧 パターンを改善"):
                        with st.spinner("パターンを改善中..."):
                            try:
                                improved_patterns = improve_regex_patterns(
                                    st.session_state.ocr_text,
                                    st.session_state.current_patterns,
                                    missing_value,
                                    selected_category
                                )
                                st.session_state.current_patterns = improved_patterns
                                st.success("✅ パターンを改善しました！")
                                st.rerun()
                            except Exception as e:
                                st.error(f"改善エラー: {str(e)}")
    
    with tab3:
        st.header("結果確認")
        
        if st.session_state.extracted_values:
            # 結果のサマリー
            st.subheader("📊 抽出結果サマリー")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("抽出数", f"{len(st.session_state.extracted_values)}個")
            with col2:
                total_amount = sum(v['normalized'] for v in st.session_state.extracted_values)
                st.metric("合計金額", f"¥{total_amount:,}")
            with col3:
                if selected_category != "自動判別":
                    st.metric("書類カテゴリ", selected_category)
            
            # バウンディングボックスでの可視化
            if st.session_state.text_elements and st.checkbox("📍 抽出位置を可視化"):
                st.subheader("抽出位置の可視化")
                
                try:
                    # PDFに抽出位置を描画
                    doc = fitz.open(temp_pdf_path)
                    page = doc[0]
                    
                    # 抽出された値の位置を特定してハイライト
                    for value in st.session_state.extracted_values:
                        # テキスト要素から該当箇所を探す
                        for element in st.session_state.text_elements:
                            if value['raw'] in element['text']:
                                rect = fitz.Rect(
                                    element['x'],
                                    element['y'],
                                    element['x'] + element['width'],
                                    element['y'] + element['height']
                                )
                                page.draw_rect(rect, color=(1, 0, 0), fill=(1, 1, 0), overlay=True, fill_opacity=0.3)
                    
                    # 画像として表示
                    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                    img_data = pix.tobytes()
                    img = Image.open(io.BytesIO(img_data))
                    st.image(img, caption="抽出位置（黄色でハイライト）", use_column_width=True)
                    doc.close()
                except Exception as e:
                    st.error(f"可視化エラー: {str(e)}")
            
            # 保存オプション
            st.markdown("---")
            if st.button("💾 結果を保存", type="primary", use_container_width=True):
                if save_to_db:
                    session = get_session()
                    try:
                        # 書類パターンを保存
                        if not st.session_state.document_pattern:
                            pattern = save_document_pattern(
                                selected_category if selected_category != "自動判別" else "その他財産書類",
                                st.session_state.ocr_text,
                                st.session_state.current_patterns,
                                session
                            )
                            st.session_state.document_pattern = pattern
                        else:
                            # 既存パターンを更新
                            pattern = st.session_state.document_pattern
                            pattern.regex_patterns = st.session_state.current_patterns
                            pattern.success_count += 1
                            session.commit()
                        
                        # 抽出履歴を保存
                        history = ExtractionHistory(
                            document_category=selected_category,
                            ocr_text=st.session_state.ocr_text[:1000],
                            used_patterns=st.session_state.current_patterns,
                            extracted_values=[v['normalized'] for v in st.session_state.extracted_values]
                        )
                        session.add(history)
                        session.commit()
                        
                        st.success("✅ データベースに保存しました！")
                    except Exception as e:
                        st.error(f"保存エラー: {str(e)}")
                    finally:
                        session.close()
                
                # 結果をダウンロード可能にする
                result_data = {
                    "timestamp": datetime.now().isoformat(),
                    "document_category": selected_category,
                    "patterns": st.session_state.current_patterns,
                    "extracted_values": st.session_state.extracted_values
                }
                
                result_json = json.dumps(result_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 結果をダウンロード (JSON)",
                    data=result_json,
                    file_name=f"extraction_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with tab4:
        st.header("統計情報")
        
        if save_to_db:
            session = get_session()
            try:
                # 書類パターンの統計
                patterns = session.query(DocumentPattern).all()
                
                if patterns:
                    st.subheader("📈 書類パターン統計")
                    
                    # カテゴリ別の統計
                    category_stats = {}
                    for pattern in patterns:
                        if pattern.category not in category_stats:
                            category_stats[pattern.category] = {
                                "count": 0,
                                "success": 0,
                                "failure": 0
                            }
                        category_stats[pattern.category]["count"] += 1
                        category_stats[pattern.category]["success"] += pattern.success_count
                        category_stats[pattern.category]["failure"] += pattern.failure_count
                    
                    # 統計表の表示
                    import pandas as pd
                    df = pd.DataFrame.from_dict(category_stats, orient='index')
                    df['成功率'] = df.apply(
                        lambda row: row['success'] / (row['success'] + row['failure']) * 100 
                        if (row['success'] + row['failure']) > 0 else 0, 
                        axis=1
                    )
                    df = df.round(1)
                    st.dataframe(df)
                    
                    # 最近の抽出履歴
                    st.subheader("📋 最近の抽出履歴")
                    recent_history = session.query(ExtractionHistory).order_by(
                        ExtractionHistory.created_at.desc()
                    ).limit(10).all()
                    
                    for history in recent_history:
                        with st.expander(f"{history.document_category} - {history.created_at.strftime('%Y/%m/%d %H:%M')}"):
                            st.write(f"抽出値: {history.extracted_values}")
                            st.write(f"使用パターン数: {len(history.used_patterns) if history.used_patterns else 0}")
                else:
                    st.info("まだデータがありません。書類を処理してパターンを保存してください。")
            except Exception as e:
                st.error(f"統計情報取得エラー: {str(e)}")
            finally:
                session.close()
    
    # 一時ファイルのクリーンアップ
    if os.path.exists(temp_pdf_path):
        try:
            os.remove(temp_pdf_path)
        except:
            pass

else:
    # アップロードされていない場合の表示
    st.info("👈 左のサイドバーからPDFファイルをアップロードしてください。")
    
    with st.expander("📖 使い方"):
        st.markdown("""
        ### システムの使い方
        
        1. **PDFファイルのアップロード**
           - 左側のサイドバーから財産書類のPDFファイルをアップロードします
        
        2. **書類カテゴリの選択**
           - 書類の種類を選択するか、「自動判別」を選択します
           - システムが過去の処理から類似書類を自動で判別します
        
        3. **OCR処理**
           - 「OCR実行」ボタンをクリックして文字認識を開始します
           - Azure Form Recognizerを使用して高精度な文字認識を行います
        
        4. **金額抽出**
           - AIが自動的に最適な正規表現パターンを生成します
           - 「金額を抽出」ボタンで金額情報を自動抽出します
        
        5. **結果確認と修正**
           - 抽出された金額を確認し、必要に応じて修正します
           - 抽出漏れがある場合は、AIがパターンを改善します
        
        6. **結果の保存**
           - 処理結果と正規表現パターンをデータベースに保存します
           - 次回以降、同じ種類の書類はより高速・高精度に処理されます
        
        ### 特徴
        - 🤖 AIによる自動的な正規表現生成
        - 📊 学習機能による精度向上
        - 💾 処理パターンの自動保存と再利用
        - 📈 処理統計の可視化
        """)
    
    # フッター
    st.markdown("---")
    st.caption("自己破産書類OCR処理システム v1.0 - Powered by Azure Form Recognizer & OpenAI")
