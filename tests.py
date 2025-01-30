class ThreadSafeExcelProcessor:
    def __init__(self, input_path, output_path):
        self.excel_data_builder = ExcelDataBuilder(input_path, output_path)
        self.lock = Lock()
        self.processed_numbers = self.load_processed_numbers()
        logger.info(f"Загружено {len(self.processed_numbers)} обработанных номеров.")
        self.is_numbers_ended = False

    def load_processed_numbers(self):
        if os.path.exists(self.excel_data_builder.output_path):
            try:
                processed_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
                return {self.normalize_phone_number(num) for num in processed_data['Телефон Ответчика']}
            except Exception as e:
                logger.exception(f"Ошибка при загрузке экспортной таблицы: {e}")
                return set()
        return set()

    @staticmethod
    def normalize_phone_number(phone):
        phone = str(phone).strip()
        digits = re.sub(r'\D', '', phone)  # Удалить все символы, кроме цифр
        if len(digits) == 11 and digits.startswith('7'):  # Российские номера (например, 7XXXXXXXXXX)
            return f'+{digits}'
        elif len(digits) == 10 and not digits.startswith('7'):  # Если номер содержит 10 цифр
            return f'+7{digits}'  # Преобразуем в международный формат
        logger.warning(f"Некорректный номер: {phone}")
        return None


    def filter_unprocessed_numbers(self):
        initial_count = len(self.excel_data_builder.df)
        logger.info(f"Изначально номеров для обработки: {initial_count}")

        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].astype(str)
        self.excel_data_builder.df['Телефон Ответчика'] = self.excel_data_builder.df['Телефон Ответчика'].apply(
            self.normalize_phone_number
        )
        self.excel_data_builder.df.dropna(subset=['Телефон Ответчика'], inplace=True)  # Удалить строки с некорректными номерами
        self.excel_data_builder.df = self.excel_data_builder.df[
            ~self.excel_data_builder.df['Телефон Ответчика'].isin(self.processed_numbers)
        ]
        filtered_count = len(self.excel_data_builder.df)
        logger.info(f"Фильтрация завершена. Осталось для обработки: {filtered_count} из {initial_count}.")


    def get_next_number(self, thread_name, avd_name):
        with self.lock:
            if not self.excel_data_builder.df.empty:
                row = self.excel_data_builder.df.iloc[0]
                logger.debug(f"[{thread_name}] [{avd_name}]: Выдан номер для обработки: {row['Телефон Ответчика']}.")
                self.excel_data_builder.df = self.excel_data_builder.df.iloc[1:]
                return row
            else:
                logger.info("Все номера обработаны.")
                self.is_numbers_ended = True
                return None


    def record_valid_number(self, row):
        thread_name = threading.current_thread().name
        normalized_row_number = self.normalize_phone_number(row['Телефон Ответчика'])

        with self.lock:
            if os.path.exists(self.excel_data_builder.output_path):
                current_data = pd.read_excel(self.excel_data_builder.output_path, dtype=str, engine='openpyxl')
            else:
                current_data = pd.DataFrame(columns=self.excel_data_builder.df.columns)

            if normalized_row_number in current_data['Телефон Ответчика'].str.strip().apply(self.normalize_phone_number).values:
                logger.debug(f"[{thread_name}] Номер {normalized_row_number} уже существует, пропускаем.")
                return

            row['Телефон Ответчика'] = normalized_row_number
            updated_data = pd.concat([current_data, pd.DataFrame([row])], ignore_index=True)
            updated_data.to_excel(self.excel_data_builder.output_path, index=False, engine='openpyxl')

            self.processed_numbers.add(normalized_row_number)
            logger.info(f"[{thread_name}] Номер {normalized_row_number} добавлен в экспортную таблицу.")

class TGAppiumEmulatorAutomationApp:
    required_directories = [
        DEFAULT_EXCEL_TABLE_DIR,
        DEFAULT_APK_SAVE_DIR,
        DEFAULT_TOOLS_DIR,
        DEFAULT_TEMP_FILES_DIR,
        DEFAULT_NODE_DIR,
        DEFAULT_SDK_DIR,
        DEFAULT_JAVA_DIR
    ]
    for directory in required_directories:
        os.makedirs(directory, exist_ok=True)

    def __init__(self):
        self.terminate_flag = Event()
        self.root = tk.Tk()

        self.android_tool_manager = AndroidToolManager(
            temp_files_dir=DEFAULT_TEMP_FILES_DIR,
            sdk_dir=DEFAULT_SDK_DIR,
            java_dir=DEFAULT_JAVA_DIR,
            base_project_dir=BASE_PROJECT_DIR,
        )

        # self.node_js_installer = NodeJsInstaller(
        #     node_dir=DEFAULT_NODE_DIR,
        #     temp_files_dir=DEFAULT_TEMP_FILES_DIR,
        #     base_project_dir=BASE_PROJECT_DIR,
        # )

        self.appium_installer = AppiumInstaller(
            base_project_dir=BASE_PROJECT_DIR
        )

        self.emulator_manager = EmulatorManager()
        self.emulator_auth_window_manager = EmulatorAuthWindowManager(self.root)
        self.emulator_auth_config_manager = EmulatorAuthConfigManager()

        self.logic = TelegramCheckerUILogic(
            temp_files_dir=DEFAULT_TEMP_FILES_DIR,
            default_excel_dir=DEFAULT_EXCEL_TABLE_DIR,
            avd_list_info_config_file=EmulatorAuthConfigManager.CONFIG_FILE,
            emulator_manager= self.emulator_manager,
            android_tool_manager=self.android_tool_manager,
            appium_installer=self.appium_installer
        )

        self.ui = TelegramCheckerUI(self.root, self.logic, self)
        self.ui.refresh_excel_table()


    def run_multithreaded_automation(self):
        thread_name = threading.current_thread().name

        apk_version_manager = TelegramApkVersionManager(telegram_app_package="org.telegram.messenger.web")

        downloaded_apk_path = apk_version_manager.download_latest_telegram_apk(
            apk_name=APK_NAME,
            download_url=APK_URL,
            save_dir=DEFAULT_APK_SAVE_DIR
        )

        avd_names = [f"AVD_DEVICE_{i + 1}" for i in range(self.ui.num_threads.get())]

        input_excel_path = app.ui.source_excel_file_path.get()
        logger.info(f"Исходный файл таблицы: {input_excel_path}")
        output_excel_path = app.ui.export_table_path.get()
        logger.info(f"Экспортный файл таблицы: {output_excel_path}")

        ram_size = self.ui.ram_size.get()
        disk_size = self.ui.disk_size.get()
        avd_ready_timeout = self.ui.avd_ready_timeout.get()
        base_port = 5554

        emulator_auth_config_manager = EmulatorAuthConfigManager()  # Инициализируем EmulatorAuthConfigManager
        excel_processor = ThreadSafeExcelProcessor(input_excel_path, output_excel_path) # Инициализация ExcelDataBuilder

        system_image = "system-images;android-22;google_apis;x86"
        platform_version = self.get_platform_version_from_system_image(system_image)

        # Скачивание общего для всех потоков образа один раз перед началом многопоточной обработки
        logger.info(f"[{thread_name}] Проверка и скачивание {system_image} перед запуском потоков...")
        self.emulator_manager.download_system_image(system_image)
        logger.info(f"[{thread_name}] Образ {system_image} загружен и готов к использованию.")

        # Многопоточная работа с эмуляторами
        with ThreadPoolExecutor(max_workers=len(avd_names)) as executor:
            futures = []
            for avd_name in avd_names:
                future =executor.submit(
                    self.process_emulator,
                    avd_name=avd_name,
                    avd_names=avd_names,
                    base_port=base_port,
                    ram_size=ram_size,
                    disk_size=disk_size,
                    system_image=system_image,
                    apk_path=downloaded_apk_path,
                    emulator_manager=self.emulator_manager,
                    excel_processor=excel_processor,
                    platform_version=platform_version,
                    avd_ready_timeout=avd_ready_timeout,
                    apk_version_manager=apk_version_manager,
                    emulator_auth_config_manager=emulator_auth_config_manager,
                )
                futures.append(future)

            # Ждём завершения потоков
            for future in futures:
                future.result()

        logger.info(f"[{thread_name}] Обработка завершена во всех эмуляторах.")


    def process_emulator(
            self,
            avd_name: str,
            avd_names: list[str],
            base_port: int,
            ram_size: str,
            disk_size: str,
            system_image: str,
            platform_version: str,
            apk_path: str,
            emulator_manager: EmulatorManager,
            excel_processor: ThreadSafeExcelProcessor,
            apk_version_manager: TelegramApkVersionManager,
            emulator_auth_config_manager: EmulatorAuthConfigManager,
            avd_ready_timeout: int = 1200,
    ):
        """Запускает эмулятор и проверяет номера на зарегистрированность."""
        thread_name = None
        android_driver_manager = None
        appium_port = None
        emulator_port = None

        try:
            тут происходит автоматизация создания и запуска эмуляторов, appium...


            while not excel_processor.is_numbers_ended:
                if self.terminate_flag.is_set():
                    break  # Прерываем цикл, если флаг установлен

                row = excel_processor.get_next_number(thread_name=thread_name, avd_name=avd_name)
                if row is None:
                    break

                phone_number = row['Телефон Ответчика']
                formatted_phone_number = excel_processor.normalize_phone_number(phone_number)
                if not formatted_phone_number:
                    logger.warning(f"[{thread_name}] [{avd_name}]: Пропуск некорректного номера: {phone_number}.")
                    continue

                logger.info(f"[{thread_name}] [{avd_name}]: Проверка номера: {formatted_phone_number}...")

                if tg_mobile_app_automation.send_message_with_phone_number(formatted_phone_number):
                    excel_processor.record_valid_number(row)

                logger.info(f"[{thread_name}] [{avd_name}]: Жмем кнопку 'Назад'")
                driver.press_keycode(AndroidKey.BACK)

        except Exception as ex:
            thread_name = threading.current_thread().name
            logger.error(f"[{thread_name}] [{avd_name}]: Произошла ошибка с эмулятором {avd_name}: {ex}")
        finally:
            self.cleanup(thread_name=thread_name, android_driver_manager=android_driver_manager, avd_name=avd_name,
                         appium_port=appium_port, emulator_manager=emulator_manager, emulator_port=emulator_port, ui=app.ui)

            self.terminate_program_during_automation(self.ui)

        self.cleanup(
            thread_name=thread_name,
            android_driver_manager=android_driver_manager,
            avd_name=avd_name,
            appium_port=appium_port,
            emulator_manager=emulator_manager,
            emulator_port=emulator_port,
            ui=app.ui
        )

        self.terminate_program_during_automation(self.ui)