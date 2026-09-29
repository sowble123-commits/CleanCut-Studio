import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

def get_unique_filepath(out_dir, base_name, suffix, ext):
    filename = f"{base_name}{suffix}.{ext}"
    full_path = os.path.join(out_dir, filename)
    if not os.path.exists(full_path): return full_path
    counter = 1
    while True:
        filename = f"{base_name}{suffix} ({counter}).{ext}"
        full_path = os.path.join(out_dir, filename)
        if not os.path.exists(full_path): return full_path
        counter += 1

def process_upscale_to_memory(image_path, engine="고속 선명화", img_type="실사 사진", scale="2배 (2x)", denoise=True, sharpen=True, progress_callback=None):
    def report(msg, ratio):
        if progress_callback: progress_callback(msg, ratio)

    report("이미지 로드 중...", 0.1)
    pil_img = Image.open(image_path).convert("RGB")
    img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    scale_factor = 4 if "4배" in scale else 2

    report(f"노이즈 제거 및 {scale_factor}배 확대 중...", 0.4)
    if denoise:
        h_val = 10 if img_type == "일러스트 / 그래픽" else 5
        img_bgr = cv2.fastNlMeansDenoisingColored(img_bgr, None, h_val, h_val, 7, 21)

    if engine == "고속 선명화":
        res_bgr = cv2.resize(img_bgr, (0,0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    else:
        res_bgr = cv2.resize(img_bgr, (0,0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
    
    report("후보정(Sharpening) 적용 중...", 0.8)
    if sharpen:
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]) if img_type == "일러스트 / 그래픽" else np.array([[0,-0.5,0], [-0.5,3,-0.5], [0,-0.5,0]])
        res_bgr = cv2.filter2D(res_bgr, -1, kernel)

    res_pil = Image.fromarray(cv2.cvtColor(res_bgr, cv2.COLOR_BGR2RGB))
    report("완료!", 1.0)
    return res_pil

def save_upscaled_image(pil_image, original_path, custom_out_dir="", filename_suffix="_upscaled"):
    src_dir = os.path.dirname(original_path)
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    out_dir = custom_out_dir if (custom_out_dir and os.path.isdir(custom_out_dir)) else os.path.join(src_dir, "CleanCut_결과물")
    os.makedirs(out_dir, exist_ok=True)
    out_png = get_unique_filepath(out_dir, base_name, filename_suffix, "png")
    pil_image.save(out_png, format="PNG")
    return out_dir, [out_png]