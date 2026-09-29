import os
import numpy as np
from PIL import Image

def get_unique_filepath(out_dir, base_name, suffix, ext):
    """동일한 파일명이 존재할 경우 (1), (2) 번호를 붙여 덮어쓰기를 방지합니다."""
    filename = f"{base_name}{suffix}.{ext}"
    full_path = os.path.join(out_dir, filename)
    if not os.path.exists(full_path):
        return full_path
    counter = 1
    while True:
        filename = f"{base_name}{suffix} ({counter}).{ext}"
        full_path = os.path.join(out_dir, filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1

def process_eraser_to_memory(image_path, mask_image, progress_callback=None):
    """원본 이미지와 마스크 이미지를 받아 지우개(Inpainting) 처리를 수행합니다."""
    def report(msg, ratio):
        if progress_callback:
            progress_callback(msg, ratio)

    report("지우개 엔진 초기화 중...", 0.1)
    try:
        import cv2
    except ImportError:
        raise RuntimeError("OpenCV가 설치되어 있지 않습니다.\npip install opencv-python 명령어를 실행해주세요.")

    report("이미지 및 마스크 분석 중...", 0.3)
    # PIL 이미지를 OpenCV용 BGR 배열로 변환
    original = Image.open(image_path).convert("RGB")
    img_array = np.array(original)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    # 마스크 이미지를 흑백(1채널) 배열로 변환
    mask_array = np.array(mask_image.convert("L"))

    report("주변 배경 픽셀 기반 복원 연산 중...", 0.6)
    # cv2.INPAINT_TELEA 알고리즘을 사용하여 마스크 영역 복원
    result_bgr = cv2.inpaint(img_bgr, mask_array, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

    report("결과물 변환 중...", 0.9)
    # 다시 BGR에서 RGB를 거쳐 PIL 이미지로 변환
    result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
    result_pil = Image.fromarray(result_rgb)

    report("복원 완료!", 1.0)
    return result_pil

def save_erased_image(pil_image, original_path, custom_out_dir="", filename_suffix="_erased"):
    """복원된 이미지를 JPG 포맷으로 저장합니다."""
    src_dir = os.path.dirname(original_path)
    base_name = os.path.splitext(os.path.basename(original_path))[0]

    if custom_out_dir and os.path.isdir(custom_out_dir):
        out_dir = custom_out_dir
    else:
        out_dir = os.path.join(src_dir, "CleanCut_결과물")
    os.makedirs(out_dir, exist_ok=True)

    out_jpg = get_unique_filepath(out_dir, base_name, filename_suffix, "jpg")
    pil_image.save(out_jpg, format="JPG", quality=95)

    return out_dir, [out_jpg]