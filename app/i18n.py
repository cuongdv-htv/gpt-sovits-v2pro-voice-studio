# -*- coding: utf-8 -*-
"""Song ngữ Việt–Nhật cho toàn bộ UI. Mọi chuỗi hiển thị đều lấy từ đây."""

LANG_VI = "vi"
LANG_JA = "ja"

STRINGS = {
    # ---- App / chung ----
    "app_title": {
        "vi": "GPT-SoVITS v2Pro Voice Studio",
        "ja": "GPT-SoVITS v2Pro ボイススタジオ",
    },
    "btn_lang_toggle": {"vi": "日本語", "ja": "VI"},
    "ok": {"vi": "OK", "ja": "OK"},
    "cancel": {"vi": "Hủy", "ja": "キャンセル"},
    "browse": {"vi": "Chọn…", "ja": "参照…"},
    "error": {"vi": "Lỗi", "ja": "エラー"},
    "warning": {"vi": "Cảnh báo", "ja": "警告"},
    "info": {"vi": "Thông báo", "ja": "お知らせ"},

    # ---- Voice clone panel ----
    "grp_voice": {"vi": "Giọng mẫu (Voice clone)", "ja": "参照音声（ボイスクローン）"},
    "ref_audio": {"vi": "Audio mẫu (3–10 giây, giọng sạch):", "ja": "参照音声（3～10秒、クリアな声）:"},
    "ref_audio_placeholder": {
        "vi": "Kéo-thả hoặc chọn file wav/mp3…",
        "ja": "wav/mp3 をドラッグ＆ドロップまたは選択…",
    },
    "btn_play_ref": {"vi": "▶ Nghe thử", "ja": "▶ 試聴"},
    "prompt_text": {"vi": "Lời thoại trong audio mẫu (prompt_text):", "ja": "参照音声のセリフ（prompt_text）:"},
    "prompt_text_placeholder": {
        "vi": "Gõ đúng nội dung nói trong audio mẫu (nên có, để trống = chế độ không text tham chiếu)",
        "ja": "参照音声の発話内容を正確に入力（推奨。空欄＝参照テキストなしモード）",
    },
    "prompt_lang": {"vi": "Ngôn ngữ của lời thoại mẫu:", "ja": "参照セリフの言語:"},
    "aux_refs": {"vi": "Audio mẫu phụ (few-shot, tùy chọn):", "ja": "補助参照音声（few-shot・任意）:"},
    "btn_add_aux": {"vi": "+ Thêm", "ja": "+ 追加"},
    "btn_remove_aux": {"vi": "− Xóa", "ja": "− 削除"},
    "grp_profiles": {"vi": "Hồ sơ giọng (Voice profiles)", "ja": "ボイスプロファイル"},
    "btn_save_profile": {"vi": "Lưu hồ sơ", "ja": "プロファイル保存"},
    "btn_load_profile": {"vi": "Nạp", "ja": "読込"},
    "btn_delete_profile": {"vi": "Xóa", "ja": "削除"},
    "profile_name_prompt": {"vi": "Tên hồ sơ giọng:", "ja": "プロファイル名:"},
    "profile_saved": {"vi": "Đã lưu hồ sơ giọng.", "ja": "プロファイルを保存しました。"},

    # ---- Input / queue ----
    "grp_input": {"vi": "Văn bản cần đọc", "ja": "読み上げテキスト"},
    "input_placeholder": {
        "vi": "Nhập văn bản cần đọc bằng giọng đã clone…",
        "ja": "クローンした声で読み上げるテキストを入力…",
    },
    "text_lang": {"vi": "Ngôn ngữ đọc:", "ja": "読み上げ言語:"},
    "text_lang_tooltip": {
        "vi": "GPT-SoVITS v2Pro chỉ hỗ trợ đọc: Trung (zh), Nhật (ja), Anh (en), Hàn (ko), Quảng Đông (yue).\n⚠ KHÔNG hỗ trợ tổng hợp tiếng Việt.",
        "ja": "GPT-SoVITS v2Pro の対応言語: 中国語(zh)・日本語(ja)・英語(en)・韓国語(ko)・広東語(yue)。\n⚠ ベトナム語の音声合成には対応していません。",
    },
    "btn_add_to_queue": {"vi": "➕ Thêm vào hàng đợi", "ja": "➕ キューに追加"},
    "btn_import_txt": {"vi": "📄 Import .txt…", "ja": "📄 .txt をインポート…"},
    "btn_import_folder": {"vi": "📁 Import thư mục…", "ja": "📁 フォルダをインポート…"},
    "grp_queue": {"vi": "Hàng đợi", "ja": "キュー"},
    "queue_col_name": {"vi": "Tên", "ja": "名前"},
    "queue_col_lang": {"vi": "Ngôn ngữ", "ja": "言語"},
    "queue_col_chars": {"vi": "Số ký tự", "ja": "文字数"},
    "queue_col_status": {"vi": "Trạng thái", "ja": "状態"},
    "btn_remove_item": {"vi": "Xóa mục", "ja": "項目を削除"},
    "btn_clear_queue": {"vi": "Xóa hết", "ja": "全て削除"},
    "btn_generate": {"vi": "🎙 Tạo (mục nhập tay)", "ja": "🎙 生成（手入力）"},
    "btn_generate_all": {"vi": "🚀 Tạo tất cả", "ja": "🚀 全て生成"},
    "btn_cancel_batch": {"vi": "⛔ Hủy", "ja": "⛔ 中止"},
    "status_pending": {"vi": "Chờ", "ja": "待機"},
    "status_running": {"vi": "Đang tạo…", "ja": "生成中…"},
    "status_done": {"vi": "Xong ✓", "ja": "完了 ✓"},
    "status_error": {"vi": "Lỗi ✗", "ja": "エラー ✗"},
    "status_skipped": {"vi": "Bỏ qua (rỗng)", "ja": "スキップ（空）"},
    "queue_empty_skip": {"vi": "Bỏ qua mục rỗng:", "ja": "空の項目をスキップ:"},

    # ---- Settings ----
    "grp_settings": {"vi": "Cài đặt", "ja": "設定"},
    "grp_engine": {"vi": "Engine GPT-SoVITS", "ja": "GPT-SoVITS エンジン"},
    "engine_folder": {"vi": "Thư mục Engine:", "ja": "エンジンフォルダ:"},
    "engine_folder_tooltip": {
        "vi": "Thư mục gói GPT-SoVITS v2Pro đã giải nén (chứa api_v2.py; gói tích hợp có runtime\\python.exe).",
        "ja": "解凍済み GPT-SoVITS v2Pro フォルダ（api_v2.py を含む。統合パッケージは runtime\\python.exe あり）。",
    },
    "host": {"vi": "Host:", "ja": "ホスト:"},
    "port": {"vi": "Port:", "ja": "ポート:"},
    "btn_start_engine": {"vi": "▶ Khởi động engine", "ja": "▶ エンジン起動"},
    "btn_stop_engine": {"vi": "■ Dừng engine", "ja": "■ エンジン停止"},
    "engine_state_stopped": {"vi": "Chưa chạy", "ja": "停止中"},
    "engine_state_starting": {"vi": "Đang khởi động… (lần đầu có thể tải model, xin chờ)", "ja": "起動中…（初回はモデルDLの場合あり）"},
    "engine_state_ready": {"vi": "Sẵn sàng", "ja": "準備完了"},
    "engine_state_error": {"vi": "Lỗi", "ja": "エラー"},
    "engine_not_ready_msg": {
        "vi": "Engine chưa sẵn sàng. Hãy trỏ đúng thư mục Engine và bấm 'Khởi động engine'.",
        "ja": "エンジンが未起動です。エンジンフォルダを設定し「エンジン起動」を押してください。",
    },
    "engine_folder_invalid": {
        "vi": "Không tìm thấy api_v2.py trong thư mục Engine. Hãy kiểm tra lại đường dẫn.",
        "ja": "エンジンフォルダに api_v2.py が見つかりません。パスを確認してください。",
    },
    "engine_python_missing": {
        "vi": "Không tìm thấy Python của engine (runtime\\python.exe). Có thể chỉ định thủ công trong Settings.",
        "ja": "エンジンの Python（runtime\\python.exe）が見つかりません。設定で手動指定できます。",
    },
    "engine_python_path": {"vi": "Python của engine (tùy chọn):", "ja": "エンジンの Python（任意）:"},
    "engine_start_failed": {"vi": "Khởi động engine thất bại. Xem log để biết chi tiết.", "ja": "エンジンの起動に失敗しました。ログを確認してください。"},
    "cpu_warning": {
        "vi": "⚠ Không phát hiện GPU NVIDIA — engine sẽ chạy CPU (RẤT chậm) nhưng vẫn hoạt động.",
        "ja": "⚠ NVIDIA GPU 未検出 — CPU 動作（非常に低速）になりますが使用可能です。",
    },

    "grp_model": {"vi": "Model", "ja": "モデル"},
    "model_variant": {"vi": "Phiên bản model:", "ja": "モデルバージョン:"},
    "gpt_weights": {"vi": "GPT weights (.ckpt):", "ja": "GPT 重み (.ckpt):"},
    "sovits_weights": {"vi": "SoVITS weights (.pth):", "ja": "SoVITS 重み (.pth):"},
    "btn_apply_model": {"vi": "Áp dụng model", "ja": "モデル適用"},
    "model_applied": {"vi": "Đã nạp model vào engine.", "ja": "モデルをエンジンに読み込みました。"},
    "model_apply_failed": {"vi": "Nạp model thất bại:", "ja": "モデル読込に失敗:"},
    "model_auto_hint": {
        "vi": "Để trống = dùng model mặc định trong tts_infer.yaml của engine.",
        "ja": "空欄＝エンジンの tts_infer.yaml の既定モデルを使用。",
    },

    "grp_synth": {"vi": "Tổng hợp", "ja": "合成"},
    "speed": {"vi": "Tốc độ đọc:", "ja": "話速:"},
    "cut_method": {"vi": "Cách cắt câu:", "ja": "文分割方法:"},
    "cut0": {"vi": "cut0 — không cắt", "ja": "cut0 — 分割なし"},
    "cut1": {"vi": "cut1 — mỗi 4 câu", "ja": "cut1 — 4文ごと"},
    "cut2": {"vi": "cut2 — mỗi ~50 ký tự", "ja": "cut2 — 約50文字ごと"},
    "cut3": {"vi": "cut3 — theo dấu 。", "ja": "cut3 — 「。」で分割"},
    "cut4": {"vi": "cut4 — theo dấu .", "ja": "cut4 — 「.」で分割"},
    "cut5": {"vi": "cut5 — theo dấu câu (khuyên dùng)", "ja": "cut5 — 句読点で分割（推奨）"},
    "grp_advanced": {"vi": "Nâng cao", "ja": "詳細設定"},
    "seed": {"vi": "Seed:", "ja": "シード:"},
    "seed_random": {"vi": "Ngẫu nhiên (-1)", "ja": "ランダム (-1)"},
    "seed_fixed": {"vi": "Cố định", "ja": "固定"},
    "grp_output": {"vi": "Đầu ra", "ja": "出力"},
    "out_format": {"vi": "Định dạng:", "ja": "フォーマット:"},
    "out_mp3_too": {"vi": "Xuất thêm MP3", "ja": "MP3 も出力"},
    "output_base": {"vi": "Thư mục lưu:", "ja": "保存先フォルダ:"},
    "btn_open_output": {"vi": "📂 Mở thư mục", "ja": "📂 フォルダを開く"},

    # ---- Bottom: progress / log / results ----
    "grp_progress": {"vi": "Tiến độ", "ja": "進行状況"},
    "progress_item": {"vi": "Mục hiện tại:", "ja": "現在の項目:"},
    "progress_total": {"vi": "Tổng:", "ja": "全体:"},
    "grp_log": {"vi": "Log", "ja": "ログ"},
    "grp_results": {"vi": "Kết quả", "ja": "結果"},
    "results_col_folder": {"vi": "Thư mục", "ja": "フォルダ"},
    "results_col_source": {"vi": "Nguồn", "ja": "ソース"},
    "results_col_open": {"vi": "Mở", "ja": "開く"},
    "btn_open_folder": {"vi": "Mở thư mục", "ja": "フォルダを開く"},
    "player_output": {"vi": "Nghe kết quả:", "ja": "出力を再生:"},

    # ---- Messages ----
    "msg_need_ref": {
        "vi": "Chưa chọn audio mẫu. Hãy chọn một file audio 3–10 giây của giọng cần clone (engine từ chối file ngoài khoảng này).",
        "ja": "参照音声が未選択です。クローンしたい声の3～10秒の音声を選択してください（範囲外はエンジンが拒否します）。",
    },
    "msg_ref_not_found": {"vi": "Không tìm thấy file audio mẫu:", "ja": "参照音声ファイルが見つかりません:"},
    "msg_need_text": {"vi": "Chưa nhập văn bản cần đọc.", "ja": "読み上げテキストが未入力です。"},
    "msg_queue_empty": {"vi": "Hàng đợi trống. Hãy thêm văn bản hoặc import file .txt.", "ja": "キューが空です。テキスト追加か .txt をインポートしてください。"},
    "msg_batch_done": {"vi": "Hoàn tất: {ok} thành công, {fail} lỗi / {total} mục.", "ja": "完了: 成功 {ok}・失敗 {fail} / 全 {total} 件。"},
    "msg_batch_cancelled": {"vi": "Đã hủy batch.", "ja": "バッチを中止しました。"},
    "msg_vram": {
        "vi": "Có thể GPU hết VRAM. Thử giảm batch_size, đóng ứng dụng khác, hoặc dùng văn bản ngắn hơn.",
        "ja": "GPU の VRAM 不足の可能性。batch_size を下げる、他アプリを閉じる、短い文を試してください。",
    },
    "msg_lang_unsupported": {
        "vi": "Ngôn ngữ không được hỗ trợ. v2Pro chỉ đọc: zh, ja, en, ko, yue (tiếng Việt KHÔNG hỗ trợ).",
        "ja": "非対応の言語です。v2Pro の対応: zh・ja・en・ko・yue（ベトナム語は非対応）。",
    },
    "msg_confirm_clear": {"vi": "Xóa toàn bộ hàng đợi?", "ja": "キューを全て削除しますか？"},
    "log_saved_to": {"vi": "Đã lưu:", "ja": "保存先:"},
    "log_engine_starting": {"vi": "Đang khởi động engine…", "ja": "エンジン起動中…"},
    "log_engine_ready": {"vi": "Engine sẵn sàng.", "ja": "エンジン準備完了。"},
    "log_engine_stopped": {"vi": "Engine đã dừng.", "ja": "エンジンを停止しました。"},
    "vi_not_supported_note": {
        "vi": "⚠ Lưu ý: v2Pro KHÔNG đọc được tiếng Việt. Ngôn ngữ đọc: zh / ja / en / ko / yue / auto.",
        "ja": "⚠ 注意: v2Pro はベトナム語読み上げ非対応。対応言語: zh / ja / en / ko / yue / auto。",
    },
}

# Ngôn ngữ đọc được hỗ trợ (KHÔNG có tiếng Việt — v2Pro không hỗ trợ)
TEXT_LANGS = ["auto", "ja", "en", "zh", "ko", "yue"]
PROMPT_LANGS = ["ja", "en", "zh", "ko", "yue"]

TEXT_LANG_LABELS = {
    "auto": {"vi": "Tự động (auto)", "ja": "自動 (auto)"},
    "ja": {"vi": "Tiếng Nhật (ja)", "ja": "日本語 (ja)"},
    "en": {"vi": "Tiếng Anh (en)", "ja": "英語 (en)"},
    "zh": {"vi": "Tiếng Trung (zh)", "ja": "中国語 (zh)"},
    "ko": {"vi": "Tiếng Hàn (ko)", "ja": "韓国語 (ko)"},
    "yue": {"vi": "Quảng Đông (yue)", "ja": "広東語 (yue)"},
}

CUT_METHODS = ["cut0", "cut1", "cut2", "cut3", "cut4", "cut5"]


class I18n:
    """Bộ chuyển ngữ đơn giản dựa trên dict."""

    def __init__(self, lang: str = LANG_VI):
        self.lang = lang if lang in (LANG_VI, LANG_JA) else LANG_VI

    def toggle(self) -> str:
        self.lang = LANG_JA if self.lang == LANG_VI else LANG_VI
        return self.lang

    def tr(self, key: str) -> str:
        entry = STRINGS.get(key)
        if not entry:
            return key
        return entry.get(self.lang, entry.get(LANG_VI, key))

    def lang_label(self, code: str) -> str:
        entry = TEXT_LANG_LABELS.get(code)
        if not entry:
            return code
        return entry.get(self.lang, code)
