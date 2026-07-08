# -*- coding: utf-8 -*-
"""worker.synthesize_one: retry từng câu, bỏ câu hỏng, từ điển phát âm.

Đây là lõi dùng chung cho batch GUI, hội thoại đa giọng và CLI — hỏng ở đây
là hỏng cả ba.
"""

import pytest

from app.audio_post import wav_duration
from app.engine_client import EngineError
from app.worker import SENTENCE_RETRIES, TtsJobConfig, synthesize_one
from tests.conftest import FakeClient, rule


def srt_cfg(**kw) -> TtsJobConfig:
    return TtsJobConfig(export_srt=True, fragment_interval=0.5, **kw)


# ------------------------------------------------------- retry / bỏ câu hỏng
def test_mot_cau_hong_khong_lam_mat_ca_chuong(fake_client):
    wav, entries, failed = synthesize_one(
        fake_client, srt_cfg(), "Câu một. BOOM hỏng. Câu ba.", "ja", 1)

    assert len(entries) == 2
    assert [e[2] for e in entries] == ["Câu một.", "Câu ba."]
    assert len(failed) == 1 and "BOOM" in failed[0]
    assert wav_duration(wav) == pytest.approx(2.5, abs=0.01)  # 1 + 0.5 + 1


def test_cau_hong_duoc_thu_lai_dung_so_lan(fake_client):
    # Câu lành đi kèm để văn bản không rơi vào nhánh "mọi câu đều hỏng"
    synthesize_one(fake_client, srt_cfg(), "BOOM hỏng. Câu lành.", "ja", 1)
    assert sum("BOOM" in t for t in fake_client.seen) == SENTENCE_RETRIES + 1


def test_loi_nhat_thoi_duoc_retry_cuu(fake_client):
    _wav, entries, failed = synthesize_one(
        fake_client, srt_cfg(), "FLAKY câu này. Câu kia.", "ja", 1)
    assert failed == []
    assert len(entries) == 2


def test_loi_nhat_thoi_qua_dai_thi_bo_cau():
    client = FakeClient(flaky_fails=SENTENCE_RETRIES + 1)
    _wav, entries, failed = synthesize_one(
        client, srt_cfg(), "FLAKY hỏng hẳn. Câu lành.", "ja", 1)
    assert len(failed) == 1
    assert len(entries) == 1


def test_timestamp_van_khop_sau_khi_bo_cau(fake_client):
    """Câu bị bỏ không tạo audio lẫn entry → timeline không lệch."""
    _wav, entries, _failed = synthesize_one(
        fake_client, srt_cfg(), "Một. BOOM. Ba.", "ja", 1)
    assert entries[0][0] == pytest.approx(0.0)
    assert entries[0][1] == pytest.approx(1.0, abs=0.01)
    assert entries[1][0] == pytest.approx(1.5, abs=0.01)   # 1.0 + gap 0.5


def test_tat_ca_cau_hong_thi_nem_loi(fake_client):
    """Retry không được phép che giấu sự cố thật (engine chết hẳn)."""
    with pytest.raises(EngineError):
        synthesize_one(fake_client, srt_cfg(), "BOOM một. BOOM hai.", "ja", 1)


def test_log_cb_bao_cao_retry_va_bo_cau(fake_client):
    logs = []
    synthesize_one(fake_client, srt_cfg(), "BOOM. Lành.", "ja", 1,
                   log_cb=logs.append)
    assert any("retry" in m for m in logs)
    assert any("bỏ qua câu" in m for m in logs)


def test_retries_bang_khong_thi_khong_thu_lai():
    client = FakeClient()
    with pytest.raises(EngineError):
        synthesize_one(client, srt_cfg(), "BOOM.", "ja", 1, retries=0)
    assert len(client.seen) == 1


# ------------------------------------------------------- nhánh không SRT
def test_non_srt_tra_ve_ba_gia_tri(fake_client):
    wav, entries, failed = synthesize_one(
        fake_client, TtsJobConfig(export_srt=False), "văn bản", "ja", 1)
    assert entries is None and failed == []
    assert wav_duration(wav) == pytest.approx(1.0, abs=0.01)


def test_non_srt_cung_duoc_retry(fake_client):
    synthesize_one(fake_client, TtsJobConfig(export_srt=False),
                   "FLAKY text", "ja", 1)
    assert len(fake_client.seen) == 3      # 1 lần đầu + 2 retry


def test_non_srt_hong_han_thi_nem_loi(fake_client):
    with pytest.raises(EngineError):
        synthesize_one(fake_client, TtsJobConfig(export_srt=False),
                       "BOOM", "ja", 1)


# ------------------------------------------------------- từ điển phát âm
def test_engine_nhan_ban_thay_the_srt_giu_ban_goc(fake_client):
    """Giao ước quan trọng nhất của từ điển phát âm."""
    cfg = srt_cfg(pronunciation_rules=[rule("TSMC", "ティーエスエムシー")])
    _wav, entries, _failed = synthesize_one(
        fake_client, cfg, "TSMCは強い。EUVも強い。", "ja", 1)

    assert fake_client.seen[0] == "ティーエスエムシーは強い。"   # gửi engine
    assert entries[0][2] == "TSMCは強い。"                      # vào .srt
    assert fake_client.seen[1] == "EUVも強い。"                 # không khớp rule


def test_non_srt_cung_ap_dung_tu_dien(fake_client):
    cfg = TtsJobConfig(export_srt=False,
                       pronunciation_rules=[rule("5G", "ファイブジー")])
    synthesize_one(fake_client, cfg, "5Gの時代", "ja", 1)
    assert fake_client.seen == ["ファイブジーの時代"]


def test_khong_co_tu_dien_thi_gui_nguyen_van(fake_client):
    synthesize_one(fake_client, TtsJobConfig(export_srt=False), "TSMC", "ja", 1)
    assert fake_client.seen == ["TSMC"]


# ------------------------------------------------------- hủy giữa chừng
def test_huy_giua_chung_thi_nem_SynthCancelled(fake_client):
    from app.worker import SynthCancelled
    with pytest.raises(SynthCancelled):
        synthesize_one(fake_client, srt_cfg(), "Một. Hai. Ba.", "ja", 1,
                       cancel_cb=lambda: True)
    assert fake_client.seen == []          # hủy trước cả lần gọi đầu tiên


def test_progress_cb_chay_toi_cuoi(fake_client):
    seen = []
    synthesize_one(fake_client, srt_cfg(), "Một. Hai.", "ja", 1,
                   progress_cb=seen.append)
    assert seen and seen[-1] == 80         # 10 + 70 * (2/2)
