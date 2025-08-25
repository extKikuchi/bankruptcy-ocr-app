# LLMによる正規表現生成モジュール
import openai
import re
import json
from config import OPENAI_API_KEY

# OpenAI APIキーを設定
openai.api_key = OPENAI_API_KEY

def generate_regex_patterns(ocr_text, target_values=None, document_category=None):
    """LLMを使用して金額抽出用の正規表現を生成"""
    
    # プロンプトの構築
    prompt = f"""以下のOCRテキストから金額を抽出するための正規表現パターンを生成してください。

書類カテゴリ: {document_category if document_category else '不明'}

OCRテキスト（一部）:
{ocr_text[:1500]}

要件:
1. 日本円の金額を抽出する正規表現を生成してください
2. 以下のような形式に対応してください：
   - 1,234,567円
   - ¥1,234,567
   - 1234567円
   - 金額：1,234,567
   - 残高 1,234,567
   - その他、書類に応じた金額表記

3. 金額の前後にある特定の文言（例：残高、金額、合計、等）も考慮してください
4. 複数のパターンを生成し、優先度順に並べてください

"""

    if target_values:
        prompt += f"\n特に以下の値を正しく抽出できるようにしてください:\n{target_values}\n"

    prompt += """
出力形式:
JSON形式で、以下のような構造で返してください：
{
  "patterns": [
    {
      "regex": "正規表現パターン",
      "description": "このパターンの説明",
      "priority": 1
    }
  ]
}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは正規表現のエキスパートです。日本の財産書類から金額を抽出するための最適な正規表現を生成してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content
        
        # JSONを抽出
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_json = json.loads(json_match.group())
            return [pattern["regex"] for pattern in result_json["patterns"]]
        else:
            # フォールバックパターン
            return [
                r'(?:残高|金額|合計|計|額)[：:\s]*([¥￥]?[\d,]+)円?',
                r'([¥￥][\d,]+)',
                r'([\d,]+)円',
                r'(?:[\d,]+)(?:\.[\d]+)?'
            ]
            
    except Exception as e:
        print(f"LLMエラー: {e}")
        # エラー時のフォールバックパターン
        return [
            r'(?:残高|金額|合計|計|額)[：:\s]*([¥￥]?[\d,]+)円?',
            r'([¥￥][\d,]+)',
            r'([\d,]+)円',
            r'(?:[\d,]+)(?:\.[\d]+)?'
        ]

def improve_regex_patterns(ocr_text, current_patterns, missed_values, document_category=None):
    """既存のパターンを改善"""
    
    prompt = f"""以下のOCRテキストから金額を抽出する正規表現を改善してください。

書類カテゴリ: {document_category if document_category else '不明'}

現在の正規表現パターン:
{json.dumps(current_patterns, ensure_ascii=False, indent=2)}

これらのパターンで抽出できなかった値:
{missed_values}

OCRテキスト（該当部分）:
{ocr_text[:1500]}

上記の抽出できなかった値を正しく抽出できるように、新しい正規表現パターンを追加または既存のパターンを改善してください。

出力形式:
JSON形式で、改善された正規表現パターンのリストを返してください：
{
  "patterns": ["正規表現1", "正規表現2", ...]
}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは正規表現のエキスパートです。既存のパターンを分析し、改善してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        result_text = response.choices[0].message.content
        
        # JSONを抽出
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_json = json.loads(json_match.group())
            return result_json["patterns"]
        else:
            return current_patterns
            
    except Exception as e:
        print(f"LLM改善エラー: {e}")
        return current_patterns

def extract_amounts_with_patterns(text, patterns):
    """正規表現パターンを使用して金額を抽出"""
    extracted_values = []
    
    for pattern in patterns:
        try:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # グループがある場合は最初のグループ、なければ全体
                value = match.group(1) if match.groups() else match.group(0)
                
                # 数値の正規化
                normalized_value = normalize_amount(value)
                if normalized_value:
                    extracted_values.append({
                        'raw': value,
                        'normalized': normalized_value,
                        'pattern': pattern,
                        'position': match.span()
                    })
        except Exception as e:
            print(f"パターン適用エラー: {pattern}, {e}")
    
    # 重複を除去（同じ正規化値を持つものを除去）
    unique_values = []
    seen_normalized = set()
    for value in extracted_values:
        if value['normalized'] not in seen_normalized:
            unique_values.append(value)
            seen_normalized.add(value['normalized'])
    
    return unique_values

def normalize_amount(amount_str):
    """金額文字列を正規化（数値に変換）"""
    try:
        # 全角数字を半角に変換
        amount_str = amount_str.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
        
        # 円記号、カンマ、円を除去
        amount_str = re.sub(r'[¥￥,円]', '', amount_str)
        
        # 空白を除去
        amount_str = amount_str.strip()
        
        # 数値に変換
        if amount_str:
            return int(amount_str)
        else:
            return None
    except:
        return None
