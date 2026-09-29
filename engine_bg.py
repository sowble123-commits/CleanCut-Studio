import os
from PIL import Image, ImageDraw, ImageFilter

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


def process_image_to_memory(
    image_path,
    mode="단색 배경",
    strength="표준",
    auto_crop=False,
    make_square=False,
    progress_callback=None
):
    """원본 이미지를 받아 배경 제거 및 다듬기를 수행한 뒤 PIL Image 객체(메모리)로 반환합니다."""
    def report(msg, ratio):
        if progress_callback:
            progress_callback(msg, ratio)

    report("원본 이미지 불러오는 중...", 0.15)
    im = Image.open(image_path).convert("RGBA")
    w0, h0 = im.size

    # 1. 배경 제거 방식 실행 (기존 호환 포함)
    if mode in ("일반 사진", "AI 정밀 누끼"):
        report("정밀 배경 제거 엔진 작동 중...", 0.35)
        try:
            from rembg import remove
            im = remove(im)
        except ImportError:
            raise RuntimeError(
                "정밀 배경 제거 도구(rembg)가 설치되지 않았습니다.\n"
                "pip install rembg onnxruntime 명령어를 실행해주세요."
            )
    else:
        report("단색 배경 스캔 및 투명화 중...", 0.4)
        thresh_map = {
            "낮음": 35,
            "표준": 75,
            "높음": 115,
            # 기존 명칭 호환
            "약하게 (보호)": 35,
            "표준 (권장)": 75,
            "강하게 (절삭)": 115
        }
        thresh_val = thresh_map.get(strength, 75)

        corners = [(0, 0), (w0 - 1, 0), (0, h0 - 1), (w0 - 1, h0 - 1)]
        for c in corners:
            px = im.getpixel(c)
            if px[3] > 0:
                ImageDraw.floodfill(im, c, (0, 0, 0, 0), thresh=thresh_val)

    # 2. 빈 여백 자동 자르기
    report("여백 및 비율 다듬는 중...", 0.75)
    if auto_crop:
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)

    # 3. 1:1 정사각형 맞춤
    if make_square:
        w, h = im.size
        m = max(w, h)
        sq = Image.new("RGBA", (m, m), (0, 0, 0, 0))
        sq.paste(im, ((m - w) // 2, (m - h) // 2))
        im = sq

    report("이미지 처리 완료!", 1.0)
    return im


def save_processed_image(
    pil_image,
    original_path,
    formats=None,
    custom_out_dir="",
    filename_suffix="_cut"
):
    """처리된 PIL Image 객체를 선택된 확장자들로 저장하며 중복 시 (1), (2)를 붙입니다."""
    if formats is None:
        formats = ["PNG"]

    src_dir = os.path.dirname(original_path)
    base_name = os.path.splitext(os.path.basename(original_path))[0]

    if custom_out_dir and os.path.isdir(custom_out_dir):
        out_dir = custom_out_dir
    else:
        out_dir = os.path.join(src_dir, "CleanCut_결과물")
    os.makedirs(out_dir, exist_ok=True)

    saved_files = []
    im = pil_image

    if "PNG" in formats:
        out_png = get_unique_filepath(out_dir, base_name, filename_suffix, "png")
        im.save(out_png, format="PNG")
        saved_files.append(out_png)

    if "WEBP" in formats:
        out_webp = get_unique_filepath(out_dir, base_name, filename_suffix, "webp")
        im.save(out_webp, format="WEBP", quality=95)
        saved_files.append(out_webp)

    if "ICO" in formats:
        w, h = im.size
        m = max(w, h)
        ico_sq = Image.new("RGBA", (m, m), (0, 0, 0, 0))
        ico_sq.paste(im, ((m - w) // 2, (m - h) // 2))

        sz = [256, 128, 64, 48, 32, 24, 16]
        fr = [
            ico_sq.resize((s, s), Image.Resampling.LANCZOS).filter(
                ImageFilter.UnsharpMask(0.8, 130, 2)
            )
            for s in sz
        ]
        out_ico = get_unique_filepath(out_dir, base_name, filename_suffix, "ico")
        fr[0].save(out_ico, format="ICO", sizes=[(s, s) for s in sz], append_images=fr[1:])
        saved_files.append(out_ico)

    if "JPG" in formats:
        bg_white = Image.new("RGB", im.size, (255, 255, 255))
        bg_white.paste(im, mask=im.split()[3])
        out_jpg = get_unique_filepath(out_dir, base_name, filename_suffix, "jpg")
        bg_white.save(out_jpg, format="JPG", quality=95)
        saved_files.append(out_jpg)

    return out_dir, saved_files


def remove_background_single(
    image_path,
    mode="단색 배경",
    strength="표준",
    auto_crop=False,
    make_square=False,
    formats=None,
    progress_callback=None,
    custom_out_dir="",
    filename_suffix="_cut"
):
    """단일 이미지를 즉시 변환하고 파일로 저장합니다."""
    def sub_cb(msg, r):
        if progress_callback:
            progress_callback(msg, r * 0.85)

    im = process_image_to_memory(
        image_path=image_path,
        mode=mode,
        strength=strength,
        auto_crop=auto_crop,
        make_square=make_square,
        progress_callback=sub_cb
    )
    if progress_callback:
        progress_callback("선택한 확장자로 파일 저장 중...", 0.92)

    out_dir, saved = save_processed_image(
        pil_image=im,
        original_path=image_path,
        formats=formats,
        custom_out_dir=custom_out_dir,
        filename_suffix=filename_suffix
    )
    if progress_callback:
        progress_callback("완료!", 1.0)
    return out_dir, saved