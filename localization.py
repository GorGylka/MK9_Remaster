"""English and Russian text used by the installer and its build errors."""

TEXT = {
    "subtitle": ("PS Vita · PCSB00106 v1.00 · Build 206", "PS Vita · PCSB00106 v1.00 · Билд 206"),
    "pc_game": ("PC game", "ПК-версия"),
    "vita_source": ("Vita source", "Источник Vita"),
    "real_vita": ("PS Vita console", "Реальная PS Vita"),
    "vita_files": ("Vita game folder", "Папка игры Vita"),
    "decrypted_eboot": ("Decrypted eboot.bin", "Расшифрованный eboot.bin"),
    "vita3k_folder_help": (
        "Select the installed PCSB00106 folder containing eboot.bin and Asset.",
        "Выберите папку установленной PCSB00106, в которой лежат eboot.bin и Asset.",
    ),
    "vita_folder_help": (
        "In VitaShell, use Open decrypted on PCSB00106 and copy Asset and VITATOC.txt to a folder on your PC.",
        "В VitaShell откройте PCSB00106 через Open decrypted и скопируйте Asset и VITATOC.txt в папку на ПК.",
    ),
    "vita3k_eboot_help": (
        "Right-click PCSB00106 in Vita3K and choose Other → Decrypt All SELF. The screenshot shows the menu on an example copy.",
        "Нажмите правой кнопкой по PCSB00106 в Vita3K и выберите Прочее → Расшифровать все SELF. На снимке показан пример меню.",
    ),
    "vita_eboot_help": (
        "Run START DECRYPT(SELF) in FAGDec and select eboot.bin from ux0:/FAGDec/app/PCSB00106.",
        "Запустите START DECRYPT(SELF) в FAGDec и укажите eboot.bin из ux0:/FAGDec/app/PCSB00106.",
    ),
    "eboot_not_found": (
        "Decrypted eboot.bin not found in cache/decrypted_selfs/PCSB00106. Choose it manually after decrypting.",
        "В cache/decrypted_selfs/PCSB00106 не найден расшифрованный eboot.bin. После расшифровки выберите файл вручную.",
    ),
    "invalid_eboot": (
        "Choose a decrypted eboot.bin from Vita3K or FAGDec.",
        "Выберите расшифрованный eboot.bin из Vita3K или FAGDec.",
    ),
    "hd_kratos": ("HD Kratos (", "HD-Кратос ("),
    "installed_kratos_mod": ("requires the mod to be installed", "требуется установленный мод"),
    "output": ("Output folder", "Папка результата"),
    "browse": ("Browse…", "Обзор…"),
    "license": ("xdelta3 license", "Лицензия xdelta3"),
    "build": ("Build rePatch", "Собрать rePatch"),
    "open_output": ("Open output", "Открыть результат"),
    "select_pc": ("Select MKKE.exe in the PC game folder", "Выберите MKKE.exe в папке ПК-версии"),
    "select_vita3k": ("Select the game folder containing eboot.bin and Asset", "Выберите папку игры с eboot.bin и Asset"),
    "select_vita": ("Select the folder copied from PS Vita", "Выберите папку, скопированную с PS Vita"),
    "select_eboot": ("Select the original decrypted eboot.bin", "Выберите оригинальный расшифрованный eboot.bin"),
    "select_kratos": ("Select CHAR_Kratos.xxx from the PS3-to-PC port", "Выберите CHAR_Kratos.xxx из PS3→PC порта"),
    "select_output": ("Select where to build the rePatch folder", "Выберите, куда собрать папку rePatch"),
    "vita_executable": ("Vita executable", "Исполняемый файл Vita"),
    "mk9_package": ("MK9 package", "Пакет MK9"),
    "all_files": ("All files", "Все файлы"),
    "asset_missing": ("This folder must contain an Asset subfolder.", "В этой папке должна быть подпапка Asset."),
    "valid_pc": ("Select MKKE.exe from the PC game installation.", "Выберите MKKE.exe из папки установленной ПК-версии."),
    "valid_vita3k": (
        "Select the installed Vita3K game folder containing both eboot.bin and Asset.",
        "Выберите папку установленной игры Vita3K, в которой есть eboot.bin и Asset.",
    ),
    "required_folders": (
        "Select the PC game, the Vita game folder and an output folder.",
        "Укажите ПК-версию, папку игры Vita и папку результата.",
    ),
    "required_eboot": ("Select a decrypted eboot.bin.", "Выберите расшифрованный eboot.bin."),
    "ready": ("Select your game files and an output folder.", "Выберите файлы игры и папку результата."),
    "checking": ("Checking source files…", "Проверка исходных файлов…"),
    "done_copy": ("Done. Copy the rePatch folder to ux0:/ on PS Vita.", "Готово. Скопируйте папку rePatch в ux0:/ на PS Vita."),
    "stopped": ("Build stopped. Check the source files.", "Сборка остановлена. Проверьте входные файлы."),
    "wait_before_exit": ("Wait for the build to finish before closing.", "Дождитесь завершения сборки перед выходом."),
    "missing_file": ("File not found: {path}\n{hint}", "Файл не найден: {path}\n{hint}"),
    "wrong_source_file": (
        "File does not match the supported original: {path}\n{hint}",
        "Файл отличается от поддерживаемого оригинала: {path}\n{hint}",
    ),
    "wrong_result": ("The build checksum does not match: {name}.", "Контрольная сумма сборки не совпала: {name}."),
    "delta_error": ("Could not apply patch {name}.\n{detail}", "Не удалось применить патч {name}.\n{detail}"),
    "unpacked_data": ("unpacked data", "распакованные данные"),
    "packed_data": ("intermediate package", "промежуточная упаковка"),
    "wrong_elf": ("Invalid ARM ELF header.", "Неверный заголовок ARM ELF."),
    "wrong_eboot_layout": ("Unexpected original eboot.bin layout.", "Неизвестная разметка оригинального eboot.bin."),
    "select_clean_eboot": (
        "Select the decrypted eboot.bin from FAGDec or Vita3K.",
        "Выберите расшифрованный eboot.bin из FAGDec или Vita3K.",
    ),
    "encrypted_self": (
        "The SELF is still encrypted. Use FAGDec or Decrypt All SELF in Vita3K.",
        "SELF всё ещё зашифрован. Используйте FAGDec или Расшифровать все SELF в Vita3K.",
    ),
    "unsupported_eboot_segment": (
        "An eboot.bin segment is damaged or uses an unsupported format.",
        "Сегмент eboot.bin повреждён или записан в неподдерживаемом формате.",
    ),
    "unpack_eboot_segment": ("Could not unpack an eboot.bin segment.", "Не удалось распаковать сегмент eboot.bin."),
    "eboot_segment_name": (
        "original PCSB00106 v1.00 eboot.bin segment", "сегмент оригинального eboot.bin PCSB00106 v1.00",
    ),
    "original_eboot": ("original eboot.bin", "оригинальный eboot.bin"),
    "read_eboot": (
        "Could not read eboot.bin. Select the original decrypted SELF for PCSB00106 v1.00.",
        "Не удалось прочитать eboot.bin. Выберите оригинальный расшифрованный SELF PCSB00106 v1.00.",
    ),
    "patched_eboot": ("eboot.bin 960×544 / 222 MHz", "eboot.bin 960×544 / 222 МГц"),
    "output_inside_source": (
        "Select an output folder outside the game installations.", "Выберите папку результата вне папок установленных игр.",
    ),
    "output_exists": (
        "This folder already exists: {path}\nSelect a different output folder.",
        "Папка уже существует: {path}\nВыберите другую папку для результата.",
    ),
    "clean_vita_hint": (
        "Use clean decrypted files from PCSB00106 v1.00 without previous mod files.",
        "Укажите чистые расшифрованные данные PCSB00106 v1.00 без файлов старого мода.",
    ),
    "pc_hint": (
        "Use the original file from Mortal Kombat Komplete Edition for PC.",
        "Требуется оригинальный файл Mortal Kombat Komplete Edition для ПК.",
    ),
    "kratos_hint": (
        "HD Kratos requires CHAR_Kratos.xxx from the compatible PS3-to-PC port.",
        "Для HD-Кратоса нужен CHAR_Kratos.xxx из совместимого PS3→PC порта.",
    ),
    "building_asset": ("Building {name}", "Сборка {name}"),
    "checking_toc": ("Checking VITATOC and preparing rePatch", "Проверка VITATOC и подготовка папки rePatch"),
    "done": ("Done", "Готово"),
    "chunk_table": ("Invalid .xxx chunk table.", "Неверная таблица блоков .xxx."),
    "read_chunk": ("Could not read a compressed .xxx chunk.", "Не удалось прочитать сжатый блок .xxx."),
    "chunk_size": ("The unpacked .xxx chunk size does not match.", "Размер распакованного блока .xxx не совпадает."),
    "chunk_incomplete": ("The compressed .xxx chunk is incomplete.", "Данные сжатого блока .xxx неполные."),
    "chunk_overlap": ("Compressed .xxx chunks overlap.", "Сжатые блоки .xxx перекрываются."),
    "packed_chunk_size": ("The compressed .xxx chunk size does not match.", "Размер сжатого блока .xxx не совпадает."),
    "first_chunk_offset": ("Invalid first Vita chunk offset.", "Неверное смещение первого блока Vita."),
    "chunk_offset": ("Invalid Vita chunk offset.", "Неверное смещение блока Vita."),
    "toc_rows_missing": ("VITATOC.txt is missing these rows: {names}.", "В VITATOC.txt отсутствуют строки: {names}."),
}


def text(language, key, **fields):
    return TEXT[key][int(language == "ru")].format(**fields)


class BuildError(ValueError):
    def __init__(self, key, **fields):
        self.key = key
        self.fields = fields
        super().__init__(self.localized("en"))

    def localized(self, language):
        fields = {name: value.localized(language) if isinstance(value, BuildError) else value
                  for name, value in self.fields.items()}
        return text(language, self.key, **fields)
