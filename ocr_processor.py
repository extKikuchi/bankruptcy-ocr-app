# OCR処理モジュール（pdf2image版）
from pdf2image import convert_from_bytes
from PIL import Image
import io
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from google.cloud import vision
from google.oauth2 import service_account
import os
import json

def pdf_to_images(pdf_path):
    """PDFを画像に変換（pdf2image版）"""
    # PDFファイルを読み込み
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
    
    # PDFを画像に変換
    images = convert_from_bytes(pdf_data, dpi=200)
    
    # バイト形式に変換
    image_bytes = []
    for img in images:
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        image_bytes.append(img_byte_arr)
    
    return image_bytes

def perform_azure_ocr(pdf_data):
    """Azure Form Recognizerを実行"""
    # 環境変数から設定を取得
    azure_endpoint = os.getenv('AZURE_ENDPOINT')
    azure_api_key = os.getenv('AZURE_API_KEY')
    azure_model_id = os.getenv('AZURE_MODEL_ID', 'prebuilt-read')
    
    if not azure_endpoint or not azure_api_key:
        raise ValueError("Azure Form Recognizerの設定が不足しています")
    
    client = DocumentAnalysisClient(
        endpoint=azure_endpoint,
        credential=AzureKeyCredential(azure_api_key)
    )
    
    poller = client.begin_analyze_document(
        azure_model_id,
        document=pdf_data
    )
    
    result = poller.result()
    
    # テキストを抽出
    full_text = ""
    for page in result.pages:
        for line in page.lines:
            full_text += line.content + "\n"
    
    return full_text.strip()

def perform_google_ocr(pdf_path):
    """Google OCRを実行"""
    # 環境変数から認証情報を取得
    google_credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if not google_credentials_json:
        raise ValueError("Google Cloud Vision APIの認証情報が設定されていません")
    
    credentials_dict = json.loads(google_credentials_json)
    credentials = service_account.Credentials.from_service_account_info(credentials_dict)
    client = vision.ImageAnnotatorClient(credentials=credentials)
    
    images = pdf_to_images(pdf_path)
    full_text = ""
    
    for img_data in images:
        image = vision.Image(content=img_data)
        response = client.text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Google OCR Error: {response.error.message}")
        
        if response.text_annotations:
            # 最初のアノテーションが全体のテキスト
            full_text += response.text_annotations[0].description + "\n"
    
    return full_text.strip()

def extract_text_with_coordinates(pdf_data, use_azure=True):
    """座標情報付きでテキストを抽出"""
    if use_azure:
        # 環境変数から設定を取得
        azure_endpoint = os.getenv('AZURE_ENDPOINT')
        azure_api_key = os.getenv('AZURE_API_KEY')
        azure_model_id = os.getenv('AZURE_MODEL_ID', 'prebuilt-read')
        
        if not azure_endpoint or not azure_api_key:
            raise ValueError("Azure Form Recognizerの設定が不足しています")
        
        client = DocumentAnalysisClient(
            endpoint=azure_endpoint,
            credential=AzureKeyCredential(azure_api_key)
        )
        
        poller = client.begin_analyze_document(
            azure_model_id,
            document=pdf_data
        )
        
        result = poller.result()
        
        text_elements = []
        for page in result.pages:
            for line in page.lines:
                if hasattr(line, 'polygon') and line.polygon:
                    x_coords = [p.x for p in line.polygon]
                    y_coords = [p.y for p in line.polygon]
                    text_elements.append({
                        'text': line.content,
                        'x': min(x_coords) * 72,  # インチからポイントへ
                        'y': min(y_coords) * 72,
                        'width': (max(x_coords) - min(x_coords)) * 72,
                        'height': (max(y_coords) - min(y_coords)) * 72,
                        'page': page.page_number - 1
                    })
        
        return text_elements
    else:
        # Google OCRの場合の実装
        return []
