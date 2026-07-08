# -*- coding: utf-8 -*-
"""settings / profiles / history — các store JSON trong %APPDATA%.

Nguyên tắc chung: file hỏng KHÔNG được làm sập app.
"""

from app.history import MAX_ENTRIES, append_history, load_history
from app.profiles import (ProfileStore, VoiceProfile, sanitize_params,
                          store_voice_files)
from app.settings import DEFAULTS, Settings


# ------------------------------------------------------------- settings
def test_settings_round_trip():
    s = Settings()
    s.set("port", 9999)
    s.set("prompt_text", "こんにちは")
    s.save()

    assert Settings().get("port") == 9999
    assert Settings().get("prompt_text") == "こんにちは"


def test_settings_bo_qua_khoa_la():
    """Khóa lạ trong file (bản cũ/tay người sửa) không được lọt vào runtime."""
    s = Settings()
    s.path.write_text('{"port": 1234, "khoa_la": "x"}', encoding="utf-8")
    reloaded = Settings()
    assert reloaded.get("port") == 1234
    assert "khoa_la" not in reloaded.data


def test_settings_file_hong_thi_dung_mac_dinh():
    s = Settings()
    s.path.write_text("{ broken", encoding="utf-8")
    assert Settings().data == DEFAULTS


def test_settings_chiu_duoc_bom():
    s = Settings()
    s.path.write_text('﻿{"port": 8888}', encoding="utf-8")
    assert Settings().get("port") == 8888


def test_settings_khoa_thieu_lay_mac_dinh():
    s = Settings()
    s.path.write_text('{"port": 1}', encoding="utf-8")
    assert Settings().get("speed_factor") == DEFAULTS["speed_factor"]


# ------------------------------------------------------------- profiles
def test_profile_upsert_va_get():
    store = ProfileStore()
    store.upsert(VoiceProfile("MC nữ", "ref.wav", "lời thoại", "ja"))
    assert ProfileStore().get("MC nữ").prompt_text == "lời thoại"


def test_profile_upsert_ghi_de_cung_ten():
    store = ProfileStore()
    store.upsert(VoiceProfile("A", "1.wav", "x", "ja"))
    store.upsert(VoiceProfile("A", "2.wav", "y", "en"))
    reloaded = ProfileStore()
    assert len(reloaded.profiles) == 1
    assert reloaded.get("A").ref_audio_path == "2.wav"


def test_profile_delete():
    store = ProfileStore()
    store.upsert(VoiceProfile("A", "1.wav", "", "ja"))
    store.delete("A")
    assert ProfileStore().names() == []


def test_profile_file_hong_thi_rong():
    store = ProfileStore()
    store.path.write_text("[[[", encoding="utf-8")
    assert ProfileStore().profiles == []


def test_profile_bo_qua_muc_khong_ten():
    store = ProfileStore()
    store.path.write_text('[{"name": ""}, {"name": "OK"}]', encoding="utf-8")
    assert ProfileStore().names() == ["OK"]


def test_store_voice_files_copy_vao_kho_app(tmp_path):
    """Profile phải sống sót khi người dùng xóa/di chuyển file gốc."""
    src = tmp_path / "goc.wav"
    src.write_bytes(b"RIFF fake")
    new_ref, new_aux = store_voice_files("hồ sơ", str(src), [])

    assert new_ref != str(src)
    assert "voices" in new_ref
    src.unlink()                                  # xóa file gốc
    assert open(new_ref, "rb").read() == b"RIFF fake"


def test_store_voice_files_giu_duong_dan_khi_file_khong_ton_tai():
    new_ref, _ = store_voice_files("x", "D:/khong/ton/tai.wav", [])
    assert new_ref == "D:/khong/ton/tai.wav"


# ------------------------------------------------- profile params (#5)
def test_profile_luu_va_nap_tham_so():
    params = {"speed_factor": 0.9, "temperature": 0.7, "top_k": 20,
              "text_split_method": "cut3"}
    ProfileStore().upsert(VoiceProfile("kể chuyện", "r.wav", "", "ja",
                                       params=params))
    loaded = ProfileStore().get("kể chuyện")
    assert loaded.params == {**params}


def test_profile_cu_khong_co_params_thi_rong():
    """File profiles.json bản cũ vẫn nạp được — params = {} nghĩa là
    'giữ nguyên cài đặt hiện tại', không phải 'ép về mặc định'."""
    store = ProfileStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text('[{"name": "cu", "ref_audio_path": "r.wav"}]',
                          encoding="utf-8")
    assert ProfileStore().get("cu").params == {}


def test_profile_khong_ghi_khoa_params_khi_rong():
    store = ProfileStore()
    store.upsert(VoiceProfile("x", "r.wav", "", "ja"))
    assert "params" not in store.path.read_text(encoding="utf-8")


def test_sanitize_params_bo_khoa_la():
    out = sanitize_params({"speed_factor": 1.2, "seed": 42, "batch_size": 8,
                           "khoa_la": "x"})
    assert out == {"speed_factor": 1.2}


def test_sanitize_params_ep_kieu():
    out = sanitize_params({"top_k": "20", "temperature": "0.7"})
    assert out == {"top_k": 20, "temperature": 0.7}


def test_sanitize_params_gia_tri_rac_thi_bo_khoa_do():
    out = sanitize_params({"top_k": "không phải số", "top_p": 0.8})
    assert out == {"top_p": 0.8}


def test_sanitize_params_khong_phai_dict():
    assert sanitize_params(None) == {}
    assert sanitize_params("rác") == {}


def test_profile_params_hong_van_nap_duoc_profile():
    store = ProfileStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        '[{"name": "x", "ref_audio_path": "r.wav", "params": "hỏng"}]',
        encoding="utf-8")
    prof = ProfileStore().get("x")
    assert prof is not None and prof.params == {}


# ------------------------------------------------------------- history
def test_history_round_trip():
    append_history("D:/a")
    append_history("D:/b")
    assert load_history() == ["D:/a", "D:/b"]


def test_history_muc_trung_bi_day_len_cuoi():
    append_history("D:/a")
    append_history("D:/b")
    append_history("D:/a")
    assert load_history() == ["D:/b", "D:/a"]


def test_history_gioi_han_so_muc():
    for i in range(MAX_ENTRIES + 20):
        append_history(f"D:/{i}")
    dirs = load_history()
    assert len(dirs) == MAX_ENTRIES
    assert dirs[-1] == f"D:/{MAX_ENTRIES + 19}"   # giữ mục mới nhất


def test_history_chua_co_file_thi_rong():
    assert load_history() == []
