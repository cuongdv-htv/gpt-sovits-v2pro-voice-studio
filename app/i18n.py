# -*- coding: utf-8 -*-
"""Đa ngôn ngữ VI/JA/EN cho toàn bộ UI. Mọi chuỗi hiển thị đều lấy từ đây."""

LANGS = ["vi", "ja", "en"]
# Nhãn hiển thị trên nút chuyển: bấm sẽ sang ngôn ngữ TIẾP THEO
NEXT_LANG_LABEL = {"vi": "日本語", "ja": "English", "en": "Tiếng Việt"}

STRINGS = {
    # ---- App / chung ----
    "app_title": {
        "vi": "GPT-SoVITS v2Pro Voice Studio",
        "ja": "GPT-SoVITS v2Pro ボイススタジオ",
        "en": "GPT-SoVITS v2Pro Voice Studio",
    },
    "ok": {"vi": "OK", "ja": "OK", "en": "OK"},
    "cancel": {"vi": "Hủy", "ja": "キャンセル", "en": "Cancel"},
    "browse": {"vi": "Chọn…", "ja": "参照…", "en": "Browse…"},
    "error": {"vi": "Lỗi", "ja": "エラー", "en": "Error"},
    "warning": {"vi": "Cảnh báo", "ja": "警告", "en": "Warning"},
    "info": {"vi": "Thông báo", "ja": "お知らせ", "en": "Info"},

    # ---- Voice clone panel ----
    "grp_voice": {"vi": "Giọng mẫu (Voice clone)", "ja": "参照音声（ボイスクローン）", "en": "Reference voice (Voice clone)"},
    "ref_audio": {"vi": "Audio mẫu (3–10 giây, giọng sạch):", "ja": "参照音声（3～10秒、クリアな声）:", "en": "Reference audio (3–10 s, clean voice):"},
    "ref_audio_placeholder": {
        "vi": "Kéo-thả hoặc chọn file wav/mp3…",
        "ja": "wav/mp3 をドラッグ＆ドロップまたは選択…",
        "en": "Drag & drop or browse a wav/mp3 file…",
    },
    "btn_play_ref": {"vi": "▶ Nghe thử", "ja": "▶ 試聴", "en": "▶ Preview"},
    "prompt_text": {"vi": "Lời thoại trong audio mẫu (prompt_text):", "ja": "参照音声のセリフ（prompt_text）:", "en": "Transcript of reference audio (prompt_text):"},
    "prompt_text_placeholder": {
        "vi": "Gõ đúng nội dung nói trong audio mẫu (nên có, để trống = chế độ không text tham chiếu)",
        "ja": "参照音声の発話内容を正確に入力（推奨。空欄＝参照テキストなしモード）",
        "en": "Type exactly what is spoken in the reference audio (recommended; empty = no-reference-text mode)",
    },
    "prompt_lang": {"vi": "Ngôn ngữ của lời thoại mẫu:", "ja": "参照セリフの言語:", "en": "Reference transcript language:"},
    "btn_transcribe": {"vi": "🎤 Nhận dạng lời thoại", "ja": "🎤 セリフを自動認識", "en": "🎤 Auto-transcribe"},
    "transcribe_tooltip": {
        "vi": "Dùng Whisper (chạy trên máy) nghe audio mẫu và tự điền lời thoại + ngôn ngữ.",
        "ja": "ローカル Whisper で参照音声を聞き取り、セリフと言語を自動入力。",
        "en": "Use local Whisper to transcribe the reference audio and fill in the transcript + language.",
    },
    "transcribe_running": {
        "vi": "🎤 Đang nhận dạng… (lần đầu có thể nạp model hơi lâu)",
        "ja": "🎤 認識中…（初回はモデル読込に時間がかかる場合あり）",
        "en": "🎤 Transcribing… (first run may take a while to load the model)",
    },
    "transcribe_missing": {
        "vi": "Chưa cài faster-whisper. Chạy: .venv\\Scripts\\pip install faster-whisper",
        "ja": "faster-whisper が未インストール。実行: .venv\\Scripts\\pip install faster-whisper",
        "en": "faster-whisper is not installed. Run: .venv\\Scripts\\pip install faster-whisper",
    },
    "transcribe_failed": {"vi": "Nhận dạng thất bại:", "ja": "認識に失敗:", "en": "Transcription failed:"},
    "transcribe_done": {"vi": "🎤 Đã điền lời thoại (kiểm tra lại trước khi dùng).", "ja": "🎤 セリフを入力しました（使用前に確認してください）。", "en": "🎤 Transcript filled in (please double-check before use)."},
    "aux_refs": {"vi": "Audio mẫu phụ (few-shot, tùy chọn):", "ja": "補助参照音声（few-shot・任意）:", "en": "Auxiliary reference audio (few-shot, optional):"},
    "btn_add_aux": {"vi": "+ Thêm", "ja": "+ 追加", "en": "+ Add"},
    "btn_remove_aux": {"vi": "− Xóa", "ja": "− 削除", "en": "− Remove"},
    "grp_profiles": {"vi": "Hồ sơ giọng (Voice profiles)", "ja": "ボイスプロファイル", "en": "Voice profiles"},
    "btn_save_profile": {"vi": "Lưu hồ sơ", "ja": "プロファイル保存", "en": "Save profile"},
    "btn_load_profile": {"vi": "Nạp", "ja": "読込", "en": "Load"},
    "btn_delete_profile": {"vi": "Xóa", "ja": "削除", "en": "Delete"},
    "profile_name_prompt": {"vi": "Tên hồ sơ giọng:", "ja": "プロファイル名:", "en": "Profile name:"},
    "profile_saved": {"vi": "Đã lưu hồ sơ giọng.", "ja": "プロファイルを保存しました。", "en": "Voice profile saved."},

    # ---- Trim dialog ----
    "btn_trim": {"vi": "✂ Cắt 3–10s…", "ja": "✂ 3～10秒に切り出し…", "en": "✂ Trim to 3–10s…"},
    "trim_title": {"vi": "Cắt audio mẫu (3–10 giây)", "ja": "参照音声の切り出し（3～10秒）", "en": "Trim reference audio (3–10 seconds)"},
    "trim_start": {"vi": "Bắt đầu:", "ja": "開始:", "en": "Start:"},
    "trim_end": {"vi": "Kết thúc:", "ja": "終了:", "en": "End:"},
    "trim_length": {"vi": "Độ dài chọn:", "ja": "選択長:", "en": "Selection length:"},
    "trim_range_hint": {"vi": "cần 3–10 giây", "ja": "3～10秒が必要", "en": "must be 3–10 s"},
    "trim_play": {"vi": "▶ Nghe đoạn chọn", "ja": "▶ 選択部分を再生", "en": "▶ Play selection"},
    "trim_save": {"vi": "💾 Lưu bản cắt && dùng", "ja": "💾 切り出して使用", "en": "💾 Save trim && use"},
    "trim_load_error": {
        "vi": "Không đọc được file audio này để cắt:",
        "ja": "この音声ファイルを読み込めませんでした:",
        "en": "Could not load this audio file for trimming:",
    },

    # ---- Input / queue ----
    "grp_input": {"vi": "Văn bản cần đọc", "ja": "読み上げテキスト", "en": "Text to speak"},
    "input_placeholder": {
        "vi": "Nhập văn bản cần đọc bằng giọng đã clone…",
        "ja": "クローンした声で読み上げるテキストを入力…",
        "en": "Enter the text to be read with the cloned voice…",
    },
    "text_lang": {"vi": "Ngôn ngữ đọc:", "ja": "読み上げ言語:", "en": "Speech language:"},
    "text_lang_tooltip": {
        "vi": "GPT-SoVITS v2Pro chỉ hỗ trợ đọc: Trung (zh), Nhật (ja), Anh (en), Hàn (ko), Quảng Đông (yue).\n⚠ KHÔNG hỗ trợ tổng hợp tiếng Việt.",
        "ja": "GPT-SoVITS v2Pro の対応言語: 中国語(zh)・日本語(ja)・英語(en)・韓国語(ko)・広東語(yue)。\n⚠ ベトナム語の音声合成には対応していません。",
        "en": "GPT-SoVITS v2Pro can speak: Chinese (zh), Japanese (ja), English (en), Korean (ko), Cantonese (yue).\n⚠ Vietnamese synthesis is NOT supported.",
    },
    "btn_add_to_queue": {"vi": "➕ Thêm vào hàng đợi", "ja": "➕ キューに追加", "en": "➕ Add to queue"},
    "btn_import_txt": {"vi": "📄 Import .txt…", "ja": "📄 .txt をインポート…", "en": "📄 Import .txt…"},
    "btn_import_folder": {"vi": "📁 Import thư mục…", "ja": "📁 フォルダをインポート…", "en": "📁 Import folder…"},
    "btn_preview": {"vi": "🎧 Thử 1 câu", "ja": "🎧 1文だけ試す", "en": "🎧 Try one sentence"},
    "preview_tooltip": {
        "vi": "Tổng hợp CÂU ĐẦU TIÊN (của mục đang chọn trong hàng đợi, hoặc của ô văn bản) và phát ngay — ưng giọng rồi hãy chạy cả batch.",
        "ja": "（キューで選択中の項目、または入力欄の）最初の一文だけ合成して再生 — 声を確認してからバッチ実行。",
        "en": "Synthesize only the FIRST sentence (of the selected queue item, or the text box) and play it — check the voice before running the whole batch.",
    },
    "preview_generating": {"vi": "🎧 Đang tạo bản thử…", "ja": "🎧 試聴を生成中…", "en": "🎧 Generating preview…"},
    "preview_done": {"vi": "🎧 Bản thử sẵn sàng — đang phát.", "ja": "🎧 試聴の準備完了 — 再生中。", "en": "🎧 Preview ready — playing."},
    # ---- Dialogue (hội thoại đa giọng) ----
    "btn_dialogue": {"vi": "🎭 Hội thoại đa giọng…", "ja": "🎭 マルチボイス会話…", "en": "🎭 Multi-voice dialogue…"},
    "dlg_title": {"vi": "Hội thoại đa giọng", "ja": "マルチボイス会話", "en": "Multi-voice dialogue"},
    "dlg_hint": {
        "vi": "Mỗi lời thoại một dòng, mở đầu bằng [Vai]. Mỗi vai gán một voice profile. Khoảng lặng giữa các lời thoại = fragment_interval (Nâng cao).",
        "ja": "各セリフは [役名] で始まる1行。役ごとにボイスプロファイルを割り当て。セリフ間の無音は fragment_interval（詳細設定）。",
        "en": "One line per utterance, starting with [Role]. Map each role to a voice profile. Silence between lines = fragment_interval (Advanced).",
    },
    "dlg_script_placeholder": {
        "vi": "[A] こんにちは、田中さん。\n[B] ああ、佐藤さん！お久しぶりです。\n[A] 最近どうですか？",
        "ja": "[A] こんにちは、田中さん。\n[B] ああ、佐藤さん！お久しぶりです。\n[A] 最近どうですか？",
        "en": "[A] Hello, Mr. Tanaka.\n[B] Oh, Ms. Sato! Long time no see.\n[A] How have you been?",
    },
    "dlg_scan": {"vi": "🔍 Quét vai", "ja": "🔍 役をスキャン", "en": "🔍 Scan roles"},
    "dlg_col_tag": {"vi": "Vai", "ja": "役", "en": "Role"},
    "dlg_col_profile": {"vi": "Voice profile", "ja": "ボイスプロファイル", "en": "Voice profile"},
    "dlg_generate": {"vi": "🎭 Tạo hội thoại", "ja": "🎭 会話を生成", "en": "🎭 Generate dialogue"},
    "dlg_need_profiles": {
        "vi": "Chưa có voice profile nào. Hãy lưu ít nhất 1 hồ sơ giọng (panel Giọng mẫu) trước.",
        "ja": "ボイスプロファイルがありません。先に参照音声パネルで1つ以上保存してください。",
        "en": "No voice profiles yet. Save at least one profile (Reference voice panel) first.",
    },
    "dlg_unmapped": {"vi": "Vai chưa được gán giọng hợp lệ:", "ja": "役に有効な声が割り当てられていません:", "en": "Role has no valid voice assigned:"},
    "dlg_parse_error": {
        "vi": "Kịch bản có nội dung trước tag [Vai] đầu tiên. Mỗi lời thoại phải bắt đầu bằng [Vai].",
        "ja": "最初の [役名] タグより前にテキストがあります。各セリフは [役名] で始めてください。",
        "en": "The script has text before the first [Role] tag. Every utterance must start with [Role].",
    },
    "dlg_parse_empty": {"vi": "Kịch bản trống hoặc không có lời thoại hợp lệ.", "ja": "台本が空か、有効なセリフがありません。", "en": "The script is empty or has no valid utterances."},
    "dlg_running": {"vi": "Đang tạo hội thoại…", "ja": "会話を生成中…", "en": "Generating dialogue…"},
    "dlg_done": {"vi": "✓ Xong:", "ja": "✓ 完了:", "en": "✓ Done:"},

    "grp_queue": {"vi": "Hàng đợi", "ja": "キュー", "en": "Queue"},
    "queue_col_name": {"vi": "Tên", "ja": "名前", "en": "Name"},
    "queue_col_lang": {"vi": "Ngôn ngữ", "ja": "言語", "en": "Language"},
    "queue_col_chars": {"vi": "Số ký tự", "ja": "文字数", "en": "Chars"},
    "queue_col_status": {"vi": "Trạng thái", "ja": "状態", "en": "Status"},
    "btn_remove_item": {"vi": "Xóa mục", "ja": "項目を削除", "en": "Remove"},
    "btn_clear_queue": {"vi": "Xóa hết", "ja": "全て削除", "en": "Clear all"},
    "btn_edit_item": {"vi": "✏ Sửa văn bản", "ja": "✏ テキスト編集", "en": "✏ Edit text"},
    "edit_item_title": {"vi": "Sửa văn bản mục:", "ja": "項目のテキストを編集:", "en": "Edit item text:"},
    "tip_move_up": {"vi": "Chuyển mục đã chọn lên trên", "ja": "選択項目を上へ移動", "en": "Move selected item up"},
    "tip_move_down": {"vi": "Chuyển mục đã chọn xuống dưới", "ja": "選択項目を下へ移動", "en": "Move selected item down"},
    "queue_drop_hint": {
        "vi": "Mẹo: kéo-thả file .txt (hoặc cả thư mục) thẳng vào bảng này.",
        "ja": "ヒント: .txt ファイル（またはフォルダ）をこの表に直接ドロップできます。",
        "en": "Tip: drag & drop .txt files (or a folder) directly onto this table.",
    },
    "btn_generate": {"vi": "🎙 Tạo (mục nhập tay)", "ja": "🎙 生成（手入力）", "en": "🎙 Generate (manual)"},
    "btn_generate_all": {"vi": "🚀 Tạo tất cả", "ja": "🚀 全て生成", "en": "🚀 Generate all"},
    "btn_retry_errors": {"vi": "🔁 Chạy lại mục lỗi", "ja": "🔁 エラー項目を再実行", "en": "🔁 Retry failed items"},
    "msg_no_error_items": {"vi": "Không có mục lỗi nào để chạy lại.", "ja": "再実行するエラー項目はありません。", "en": "There are no failed items to retry."},
    "btn_cancel_batch": {"vi": "⛔ Hủy", "ja": "⛔ 中止", "en": "⛔ Cancel"},
    "status_pending": {"vi": "Chờ", "ja": "待機", "en": "Pending"},
    "status_running": {"vi": "Đang tạo…", "ja": "生成中…", "en": "Running…"},
    "status_done": {"vi": "Xong ✓", "ja": "完了 ✓", "en": "Done ✓"},
    "status_error": {"vi": "Lỗi ✗", "ja": "エラー ✗", "en": "Error ✗"},
    "status_skipped": {"vi": "Bỏ qua (rỗng)", "ja": "スキップ（空）", "en": "Skipped (empty)"},
    "queue_empty_skip": {"vi": "Bỏ qua mục rỗng:", "ja": "空の項目をスキップ:", "en": "Skipping empty item:"},

    # ---- Settings: engine ----
    "grp_engine": {"vi": "Engine GPT-SoVITS", "ja": "GPT-SoVITS エンジン", "en": "GPT-SoVITS engine"},
    "engine_folder": {"vi": "Thư mục Engine:", "ja": "エンジンフォルダ:", "en": "Engine folder:"},
    "engine_folder_tooltip": {
        "vi": "Thư mục gói GPT-SoVITS v2Pro đã giải nén (chứa api_v2.py; gói tích hợp có runtime\\python.exe).",
        "ja": "解凍済み GPT-SoVITS v2Pro フォルダ（api_v2.py を含む。統合パッケージは runtime\\python.exe あり）。",
        "en": "Extracted GPT-SoVITS v2Pro folder (contains api_v2.py; the integrated package has runtime\\python.exe).",
    },
    "host": {"vi": "Host:", "ja": "ホスト:", "en": "Host:"},
    "port": {"vi": "Port:", "ja": "ポート:", "en": "Port:"},
    "auto_start_engine": {
        "vi": "Tự khởi động engine khi mở app",
        "ja": "アプリ起動時にエンジンを自動起動",
        "en": "Auto-start engine when the app opens",
    },
    "btn_start_engine": {"vi": "▶ Khởi động engine", "ja": "▶ エンジン起動", "en": "▶ Start engine"},
    "btn_stop_engine": {"vi": "■ Dừng engine", "ja": "■ エンジン停止", "en": "■ Stop engine"},
    "engine_state_stopped": {"vi": "Chưa chạy", "ja": "停止中", "en": "Not running"},
    "engine_state_starting": {"vi": "Đang khởi động… (lần đầu có thể tải model, xin chờ)", "ja": "起動中…（初回はモデルDLの場合あり）", "en": "Starting… (first run may download models)"},
    "engine_state_ready": {"vi": "Sẵn sàng", "ja": "準備完了", "en": "Ready"},
    "engine_state_error": {"vi": "Lỗi", "ja": "エラー", "en": "Error"},
    "engine_state_crashed": {
        "vi": "Engine dừng đột ngột — bấm 'Khởi động engine' để chạy lại",
        "ja": "エンジンが異常終了 — 「エンジン起動」で再起動してください",
        "en": "Engine crashed — click 'Start engine' to restart",
    },
    "log_engine_crashed": {
        "vi": "💥 Engine dừng đột ngột (tiến trình đã thoát). Xem các dòng [engine] phía trên để biết nguyên nhân.",
        "ja": "💥 エンジンが異常終了しました（プロセス終了）。原因は上の [engine] 行を確認してください。",
        "en": "💥 Engine crashed (process exited). Check the [engine] lines above for the cause.",
    },
    "engine_not_ready_msg": {
        "vi": "Engine chưa sẵn sàng. Hãy trỏ đúng thư mục Engine và bấm 'Khởi động engine'.",
        "ja": "エンジンが未起動です。エンジンフォルダを設定し「エンジン起動」を押してください。",
        "en": "Engine is not ready. Set the engine folder and click 'Start engine'.",
    },
    "engine_folder_invalid": {
        "vi": "Không tìm thấy api_v2.py trong thư mục Engine. Hãy kiểm tra lại đường dẫn.",
        "ja": "エンジンフォルダに api_v2.py が見つかりません。パスを確認してください。",
        "en": "api_v2.py was not found in the engine folder. Please check the path.",
    },
    "engine_python_missing": {
        "vi": "Không tìm thấy Python của engine (runtime\\python.exe). Có thể chỉ định thủ công trong Settings.",
        "ja": "エンジンの Python（runtime\\python.exe）が見つかりません。設定で手動指定できます。",
        "en": "Engine Python (runtime\\python.exe) not found. You can set it manually in Settings.",
    },
    "engine_python_path": {"vi": "Python của engine (tùy chọn):", "ja": "エンジンの Python（任意）:", "en": "Engine Python (optional):"},
    "engine_start_failed": {"vi": "Khởi động engine thất bại. Xem log để biết chi tiết.", "ja": "エンジンの起動に失敗しました。ログを確認してください。", "en": "Failed to start the engine. See the log for details."},
    "cpu_warning": {
        "vi": "⚠ Không phát hiện GPU NVIDIA — engine sẽ chạy CPU (RẤT chậm) nhưng vẫn hoạt động.",
        "ja": "⚠ NVIDIA GPU 未検出 — CPU 動作（非常に低速）になりますが使用可能です。",
        "en": "⚠ No NVIDIA GPU detected — the engine will run on CPU (VERY slow) but will still work.",
    },

    # ---- Settings: model ----
    "grp_model": {"vi": "Model", "ja": "モデル", "en": "Model"},
    "model_variant": {"vi": "Phiên bản model:", "ja": "モデルバージョン:", "en": "Model variant:"},
    "gpt_weights": {"vi": "GPT weights (.ckpt):", "ja": "GPT 重み (.ckpt):", "en": "GPT weights (.ckpt):"},
    "sovits_weights": {"vi": "SoVITS weights (.pth):", "ja": "SoVITS 重み (.pth):", "en": "SoVITS weights (.pth):"},
    "btn_apply_model": {"vi": "Áp dụng model", "ja": "モデル適用", "en": "Apply model"},
    "model_applied": {"vi": "Đã nạp model vào engine.", "ja": "モデルをエンジンに読み込みました。", "en": "Model loaded into the engine."},
    "model_apply_failed": {"vi": "Nạp model thất bại:", "ja": "モデル読込に失敗:", "en": "Failed to load model:"},
    "model_auto_hint": {
        "vi": "Để trống = dùng model mặc định trong tts_infer.yaml của engine.",
        "ja": "空欄＝エンジンの tts_infer.yaml の既定モデルを使用。",
        "en": "Leave empty = use the default model from the engine's tts_infer.yaml.",
    },

    # ---- Settings: synthesis ----
    "grp_synth": {"vi": "Tổng hợp", "ja": "合成", "en": "Synthesis"},
    "speed": {"vi": "Tốc độ đọc:", "ja": "話速:", "en": "Speech speed:"},
    "cut_method": {"vi": "Cách cắt câu:", "ja": "文分割方法:", "en": "Text split method:"},
    "cut0": {"vi": "cut0 — không cắt", "ja": "cut0 — 分割なし", "en": "cut0 — no split"},
    "cut1": {"vi": "cut1 — mỗi 4 câu", "ja": "cut1 — 4文ごと", "en": "cut1 — every 4 sentences"},
    "cut2": {"vi": "cut2 — mỗi ~50 ký tự", "ja": "cut2 — 約50文字ごと", "en": "cut2 — every ~50 chars"},
    "cut3": {"vi": "cut3 — theo dấu 。", "ja": "cut3 — 「。」で分割", "en": "cut3 — split at 。"},
    "cut4": {"vi": "cut4 — theo dấu .", "ja": "cut4 — 「.」で分割", "en": "cut4 — split at ."},
    "cut5": {"vi": "cut5 — theo dấu câu (khuyên dùng)", "ja": "cut5 — 句読点で分割（推奨）", "en": "cut5 — split at punctuation (recommended)"},
    "grp_advanced": {"vi": "Nâng cao", "ja": "詳細設定", "en": "Advanced"},
    "seed": {"vi": "Seed:", "ja": "シード:", "en": "Seed:"},
    "seed_random": {"vi": "Ngẫu nhiên (-1)", "ja": "ランダム (-1)", "en": "Random (-1)"},
    "seed_fixed": {"vi": "Cố định", "ja": "固定", "en": "Fixed"},

    # ---- Settings: output ----
    "grp_output": {"vi": "Đầu ra", "ja": "出力", "en": "Output"},
    "out_format": {"vi": "Định dạng:", "ja": "フォーマット:", "en": "Format:"},
    "out_mp3_too": {"vi": "Xuất thêm MP3", "ja": "MP3 も出力", "en": "Also export MP3"},
    "out_srt": {"vi": "Xuất phụ đề .srt (đọc từng câu)", "ja": "字幕 .srt を出力（文単位で合成）", "en": "Export .srt subtitles (per-sentence)"},
    "out_srt_tooltip": {
        "vi": "Tổng hợp TỪNG CÂU để lấy timestamp chính xác → file .srt khớp giọng đọc.\nChậm hơn chế độ thường một chút; ngữ điệu nối câu có thể khác nhẹ.",
        "ja": "文ごとに合成して正確なタイムスタンプを取得 → 音声に同期した .srt を生成。\n通常モードよりやや遅く、文間の抑揚が少し変わる場合があります。",
        "en": "Synthesizes SENTENCE BY SENTENCE for exact timestamps → .srt in sync with the audio.\nSlightly slower; cross-sentence prosody may differ a little.",
    },
    "out_norm": {"vi": "Chuẩn hóa loudness −14 LUFS (YouTube)", "ja": "ラウドネス正規化 −14 LUFS（YouTube）", "en": "Normalize loudness to −14 LUFS (YouTube)"},
    "out_norm_tooltip": {
        "vi": "Chuẩn EBU R128 qua ffmpeg — âm lượng đồng đều giữa các video.",
        "ja": "ffmpeg の EBU R128 準拠 — 動画間で音量を均一化。",
        "en": "EBU R128 via ffmpeg — consistent volume across videos.",
    },
    "out_audiobook": {"vi": "Ghép batch thành 1 file (audiobook)", "ja": "バッチを1ファイルに結合（オーディオブック）", "en": "Merge batch into one file (audiobook)"},
    "out_audiobook_tooltip": {
        "vi": "Sau khi 'Tạo tất cả' xong: ghép các mục thành công thành merged.wav theo thứ tự hàng đợi (+ merged.srt nếu bật SRT).",
        "ja": "「全て生成」完了後、成功した項目をキュー順に merged.wav へ結合（SRT有効時は merged.srt も）。",
        "en": "After 'Generate all': merge successful items into merged.wav in queue order (+ merged.srt if SRT is on).",
    },
    "audiobook_gap": {"vi": "Khoảng lặng giữa các mục (giây):", "ja": "項目間の無音（秒）:", "en": "Silence between items (s):"},
    "log_audiobook_done": {"vi": "📚 Đã ghép audiobook:", "ja": "📚 オーディオブック結合完了:", "en": "📚 Audiobook merged:"},
    "output_base": {"vi": "Thư mục lưu:", "ja": "保存先フォルダ:", "en": "Output folder:"},
    "btn_open_output": {"vi": "📂 Mở thư mục", "ja": "📂 フォルダを開く", "en": "📂 Open folder"},

    # ---- Bottom ----
    "progress_item": {"vi": "Mục hiện tại:", "ja": "現在の項目:", "en": "Current item:"},
    "progress_total": {"vi": "Tổng:", "ja": "全体:", "en": "Total:"},
    "eta_prefix": {"vi": "Còn lại ≈", "ja": "残り ≈", "en": "ETA ≈"},
    "grp_log": {"vi": "Log", "ja": "ログ", "en": "Log"},
    "grp_results": {"vi": "Kết quả", "ja": "結果", "en": "Results"},
    "results_col_folder": {"vi": "Thư mục", "ja": "フォルダ", "en": "Folder"},
    "results_col_source": {"vi": "Nguồn", "ja": "ソース", "en": "Source"},
    "results_col_open": {"vi": "Mở", "ja": "開く", "en": "Open"},
    "btn_open_folder": {"vi": "Mở thư mục", "ja": "フォルダを開く", "en": "Open folder"},
    "player_output": {"vi": "Nghe kết quả:", "ja": "出力を再生:", "en": "Play result:"},
    "notif_batch_title": {"vi": "Voice Studio — xong!", "ja": "Voice Studio — 完了！", "en": "Voice Studio — done!"},

    # ---- Messages ----
    "msg_need_ref": {
        "vi": "Chưa chọn audio mẫu. Hãy chọn một file audio 3–10 giây của giọng cần clone (engine từ chối file ngoài khoảng này).",
        "ja": "参照音声が未選択です。クローンしたい声の3～10秒の音声を選択してください（範囲外はエンジンが拒否します）。",
        "en": "No reference audio selected. Choose a 3–10 second clip of the voice to clone (the engine rejects clips outside this range).",
    },
    "msg_ref_not_found": {"vi": "Không tìm thấy file audio mẫu:", "ja": "参照音声ファイルが見つかりません:", "en": "Reference audio file not found:"},
    "msg_need_text": {"vi": "Chưa nhập văn bản cần đọc.", "ja": "読み上げテキストが未入力です。", "en": "No text to speak has been entered."},
    "msg_queue_empty": {"vi": "Hàng đợi trống. Hãy thêm văn bản hoặc import file .txt.", "ja": "キューが空です。テキスト追加か .txt をインポートしてください。", "en": "The queue is empty. Add text or import .txt files."},
    "msg_batch_done": {"vi": "Hoàn tất: {ok} thành công, {fail} lỗi / {total} mục.", "ja": "完了: 成功 {ok}・失敗 {fail} / 全 {total} 件。", "en": "Finished: {ok} succeeded, {fail} failed / {total} items."},
    "msg_batch_cancelled": {"vi": "Đã hủy batch.", "ja": "バッチを中止しました。", "en": "Batch cancelled."},
    "err_ref_duration": {
        "vi": "Audio mẫu phải dài 3–10 giây — engine từ chối file ngoài khoảng này. Dùng nút '✂ Cắt 3–10s…' để cắt lại.",
        "ja": "参照音声は3～10秒である必要があります（範囲外はエンジンが拒否）。「✂ 3～10秒に切り出し…」で調整してください。",
        "en": "Reference audio must be 3–10 seconds — the engine rejects clips outside this range. Use '✂ Trim to 3–10s…' to fix it.",
    },
    "ref_dur_ok": {"vi": "✓ {d} giây — hợp lệ", "ja": "✓ {d} 秒 — OK", "en": "✓ {d} s — OK"},
    "ref_dur_bad": {
        "vi": "✗ {d} giây — ngoài 3–10s, engine sẽ từ chối. Bấm '✂ Cắt 3–10s…'",
        "ja": "✗ {d} 秒 — 3～10秒の範囲外。エンジンが拒否します。「✂ 3～10秒に切り出し…」",
        "en": "✗ {d} s — outside 3–10 s, the engine will reject it. Click '✂ Trim to 3–10s…'",
    },
    "ref_dur_unknown": {
        "vi": "⚠ Không đọc được độ dài file này",
        "ja": "⚠ この音声の長さを読み取れません",
        "en": "⚠ Cannot read the duration of this file",
    },
    "msg_vram": {
        "vi": "Có thể GPU hết VRAM. Thử giảm batch_size, đóng ứng dụng khác, hoặc dùng văn bản ngắn hơn.",
        "ja": "GPU の VRAM 不足の可能性。batch_size を下げる、他アプリを閉じる、短い文を試してください。",
        "en": "The GPU may be out of VRAM. Try lowering batch_size, closing other apps, or using shorter text.",
    },
    "msg_lang_unsupported": {
        "vi": "Ngôn ngữ không được hỗ trợ. v2Pro chỉ đọc: zh, ja, en, ko, yue (tiếng Việt KHÔNG hỗ trợ).",
        "ja": "非対応の言語です。v2Pro の対応: zh・ja・en・ko・yue（ベトナム語は非対応）。",
        "en": "Unsupported language. v2Pro speaks only zh, ja, en, ko, yue (Vietnamese is NOT supported).",
    },
    "msg_confirm_clear": {"vi": "Xóa toàn bộ hàng đợi?", "ja": "キューを全て削除しますか？", "en": "Clear the entire queue?"},
    "log_engine_starting": {"vi": "Đang khởi động engine…", "ja": "エンジン起動中…", "en": "Starting engine…"},
    "log_engine_ready": {"vi": "Engine sẵn sàng.", "ja": "エンジン準備完了。", "en": "Engine ready."},
    "log_engine_stopped": {"vi": "Engine đã dừng.", "ja": "エンジンを停止しました。", "en": "Engine stopped."},
    "vi_not_supported_note": {
        "vi": "⚠ Lưu ý: v2Pro KHÔNG đọc được tiếng Việt. Ngôn ngữ đọc: zh / ja / en / ko / yue / auto.",
        "ja": "⚠ 注意: v2Pro はベトナム語読み上げ非対応。対応言語: zh / ja / en / ko / yue / auto。",
        "en": "⚠ Note: v2Pro CANNOT speak Vietnamese. Speech languages: zh / ja / en / ko / yue / auto.",
    },
}

# Ngôn ngữ đọc được hỗ trợ (KHÔNG có tiếng Việt — v2Pro không hỗ trợ)
TEXT_LANGS = ["auto", "ja", "en", "zh", "ko", "yue"]
PROMPT_LANGS = ["ja", "en", "zh", "ko", "yue"]

TEXT_LANG_LABELS = {
    "auto": {"vi": "Tự động (auto)", "ja": "自動 (auto)", "en": "Auto-detect (auto)"},
    "ja": {"vi": "Tiếng Nhật (ja)", "ja": "日本語 (ja)", "en": "Japanese (ja)"},
    "en": {"vi": "Tiếng Anh (en)", "ja": "英語 (en)", "en": "English (en)"},
    "zh": {"vi": "Tiếng Trung (zh)", "ja": "中国語 (zh)", "en": "Chinese (zh)"},
    "ko": {"vi": "Tiếng Hàn (ko)", "ja": "韓国語 (ko)", "en": "Korean (ko)"},
    "yue": {"vi": "Quảng Đông (yue)", "ja": "広東語 (yue)", "en": "Cantonese (yue)"},
}

CUT_METHODS = ["cut0", "cut1", "cut2", "cut3", "cut4", "cut5"]


class I18n:
    """Bộ chuyển ngữ VI → JA → EN → VI dựa trên dict."""

    def __init__(self, lang: str = "vi"):
        self.lang = lang if lang in LANGS else "vi"

    def toggle(self) -> str:
        self.lang = LANGS[(LANGS.index(self.lang) + 1) % len(LANGS)]
        return self.lang

    def next_lang_label(self) -> str:
        return NEXT_LANG_LABEL[self.lang]

    def tr(self, key: str) -> str:
        entry = STRINGS.get(key)
        if not entry:
            return key
        return entry.get(self.lang, entry.get("vi", key))

    def lang_label(self, code: str) -> str:
        entry = TEXT_LANG_LABELS.get(code)
        if not entry:
            return code
        return entry.get(self.lang, code)
