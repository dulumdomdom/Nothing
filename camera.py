#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Программа для работы с фотокамерой на Altlinux p11
Функции:
- Отображение видео в реальном времени
- Создание снимков с автоматической нумерацией (название-1, название-2 и т.д.)
- Сохранение снимков сразу в две директории
- Просмотр снимков с поиском по названию
"""

import cv2
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import glob
from pathlib import Path
import json

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Фотокамера")
        self.root.geometry("1280x1024")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Настройки
        self.settings_file = Path.home() / ".camera_settings.json"
        self.dir1 = None
        self.dir2 = None
        self.view_dir = None
        self.load_settings()
        
        # Переменные
        self.cap = None
        self.is_recording = False
        self.current_photos = []
        self.search_var = tk.StringVar()
        
        # Создание интерфейса
        self.create_widgets()
        
        # Запуск камеры
        self.start_camera()
        
    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Основной фрейм
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Левая панель - видео
        left_frame = ttk.LabelFrame(main_frame, text="Видео с камеры", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.video_label = ttk.Label(left_frame)
        self.video_label.pack(expand=True)
        
        # Правая панель - управление
        right_frame = ttk.LabelFrame(main_frame, text="Управление", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # Настройки
        settings_frame = ttk.LabelFrame(right_frame, text="Настройки", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Директория 1
        ttk.Label(settings_frame, text="Директория 1:").pack(anchor=tk.W)
        self.dir1_frame = ttk.Frame(settings_frame)
        self.dir1_frame.pack(fill=tk.X, pady=(0, 5))
        self.dir1_label = ttk.Label(self.dir1_frame, text="Не выбрана", foreground="gray")
        self.dir1_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(self.dir1_frame, text="Выбрать", command=lambda: self.select_dir(1)).pack(side=tk.RIGHT)
        
        # Директория 2
        ttk.Label(settings_frame, text="Директория 2:").pack(anchor=tk.W)
        self.dir2_frame = ttk.Frame(settings_frame)
        self.dir2_frame.pack(fill=tk.X, pady=(0, 5))
        self.dir2_label = ttk.Label(self.dir2_frame, text="Не выбрана", foreground="gray")
        self.dir2_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(self.dir2_frame, text="Выбрать", command=lambda: self.select_dir(2)).pack(side=tk.RIGHT)
        
        # Папка для просмотра
        ttk.Label(settings_frame, text="Папка для просмотра:").pack(anchor=tk.W)
        self.view_frame = ttk.Frame(settings_frame)
        self.view_frame.pack(fill=tk.X)
        self.view_label = ttk.Label(self.view_frame, text="Не выбрана", foreground="gray")
        self.view_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(self.view_frame, text="Выбрать", command=self.select_view_dir).pack(side=tk.RIGHT)
        
        # Сохранение настроек
        ttk.Button(settings_frame, text="Сохранить настройки", command=self.save_settings).pack(fill=tk.X, pady=(10, 0))
        
        # Управление съемкой
        capture_frame = ttk.LabelFrame(right_frame, text="Съемка", padding=10)
        capture_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(capture_frame, text="Название снимка:").pack(anchor=tk.W)
        self.photo_name_entry = ttk.Entry(capture_frame, width=30)
        self.photo_name_entry.pack(fill=tk.X, pady=(0, 10))
        self.photo_name_entry.bind('<Return>', lambda e: self.capture_photo())
        
        # Кнопка для снимка
        self.capture_btn = ttk.Button(capture_frame, text="📸 Сделать снимок (Пробел)", 
                                      command=self.capture_photo, width=25)
        self.capture_btn.pack()
        
        # Привязка клавиши пробела
        self.root.bind('<space>', lambda e: self.capture_photo())
        
        # Просмотр
        view_frame = ttk.LabelFrame(right_frame, text="Просмотр", padding=10)
        view_frame.pack(fill=tk.BOTH, expand=True)
        
        # Поиск по названию
        ttk.Label(view_frame, text="Поиск по названию:").pack(anchor=tk.W)
        self.search_entry = ttk.Entry(view_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(fill=tk.X, pady=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.search_photos)
        
        # Список фото
        list_frame = ttk.Frame(view_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.photos_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        self.photos_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.photos_listbox.yview)
        
        self.photos_listbox.bind('<Double-Button-1>', self.view_selected_photo)
        
        # Кнопка обновления
        ttk.Button(view_frame, text="🔄 Обновить список", command=self.load_photos_for_view).pack(fill=tk.X, pady=(10, 0))
        
        # Статус
        self.status_label = ttk.Label(right_frame, text="Статус: Ожидание", 
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
    def select_dir(self, num):
        """Выбор директории для сохранения"""
        dir_path = filedialog.askdirectory(title=f"Выберите директорию {num}")
        if dir_path:
            if num == 1:
                self.dir1 = Path(dir_path)
                self.dir1_label.config(text=str(self.dir1), foreground="black")
            else:
                self.dir2 = Path(dir_path)
                self.dir2_label.config(text=str(self.dir2), foreground="black")
    
    def select_view_dir(self):
        """Выбор папки для просмотра"""
        dir_path = filedialog.askdirectory(title="Выберите папку для просмотра снимков")
        if dir_path:
            self.view_dir = Path(dir_path)
            self.view_label.config(text=str(self.view_dir), foreground="black")
            self.load_photos_for_view()
    
    def load_photos_for_view(self):
        """Загрузка списка фото из папки просмотра"""
        if not self.view_dir or not self.view_dir.exists():
            self.photos_listbox.delete(0, tk.END)
            self.photos_listbox.insert(tk.END, "Папка не выбрана")
            return
        
        # Загружаем все jpg файлы
        all_photos = sorted(self.view_dir.glob("*.jpg"))
        
        # Фильтруем по поиску
        search_text = self.search_var.get().strip().lower()
        if search_text:
            filtered_photos = [p for p in all_photos if search_text in p.stem.lower()]
        else:
            filtered_photos = all_photos
        
        self.current_photos = filtered_photos
        
        # Обновляем список
        self.photos_listbox.delete(0, tk.END)
        if not self.current_photos:
            self.photos_listbox.insert(tk.END, "Нет фотографий")
        else:
            for photo in self.current_photos:
                display_name = f"{photo.stem} ({photo.stat().st_size // 1024}KB)"
                self.photos_listbox.insert(tk.END, display_name)
        
        self.update_status(f"Найдено {len(self.current_photos)} фото")
    
    def search_photos(self, event=None):
        """Поиск фото по названию"""
        self.load_photos_for_view()
    
    def view_selected_photo(self, event=None):
        """Просмотр выбранного фото"""
        selection = self.photos_listbox.curselection()
        if selection and self.current_photos:
            selected_idx = selection[0]
            if selected_idx < len(self.current_photos):
                self.show_photo_window(self.current_photos[selected_idx])
    
    def show_photo_window(self, photo_path):
        """Отображение фото в отдельном окне"""
        view_window = tk.Toplevel(self.root)
        view_window.title(f"Просмотр: {photo_path.name}")
        
        # Размер окна под экран 1280x1024
        view_window.geometry("800x600")
        
        # Загружаем изображение
        img = Image.open(photo_path)
        
        # Масштабируем под окно
        display_img = img.copy()
        display_img.thumbnail((750, 550), Image.Resampling.LANCZOS)
        
        photo = ImageTk.PhotoImage(display_img)
        
        label = ttk.Label(view_window, image=photo)
        label.image = photo
        label.pack(expand=True, padx=10, pady=10)
        
        # Информация о фото
        info_text = f"Название: {photo_path.stem}\nРазмер: {photo_path.stat().st_size // 1024} KB"
        info_label = ttk.Label(view_window, text=info_text, justify=tk.CENTER)
        info_label.pack(pady=(0, 10))
        
        ttk.Button(view_window, text="Закрыть", command=view_window.destroy).pack(pady=(0, 10))
    
    def start_camera(self):
        """Запуск камеры"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Ошибка", "Не удалось открыть камеру!")
                return
            self.is_recording = True
            self.update_video()
            self.update_status("Камера запущена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка запуска камеры: {e}")
    
    def update_video(self):
        """Обновление видео в реальном времени"""
        if self.is_recording and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # Конвертируем BGR в RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Изменяем размер для отображения (под экран 1280x1024)
                height, width = frame_rgb.shape[:2]
                max_width = 800
                if width > max_width:
                    scale = max_width / width
                    new_width = max_width
                    new_height = int(height * scale)
                    frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Конвертируем в ImageTk
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            
            self.root.after(30, self.update_video)
    
    def capture_photo(self):
        """Создание снимка"""
        photo_name = self.photo_name_entry.get().strip()
        
        if not photo_name:
            messagebox.showwarning("Внимание", "Введите название снимка!")
            return
        
        if not self.dir1 or not self.dir2:
            messagebox.showwarning("Внимание", "Выберите обе директории для сохранения в настройках!")
            return
        
        # Получаем текущий кадр
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Ошибка", "Не удалось захватить кадр!")
            return
        
        # Сохраняем в обе директории
        saved_files = []
        
        for dir_path in [self.dir1, self.dir2]:
            # Создаем директорию если не существует
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Определяем следующий номер фотографии
            existing_files = list(dir_path.glob(f"{photo_name}-*.jpg"))
            numbers = []
            for f in existing_files:
                try:
                    num = int(f.stem.split('-')[-1])
                    numbers.append(num)
                except:
                    pass
            
            next_num = max(numbers) + 1 if numbers else 1
            
            # Формируем имя файла
            filename = f"{photo_name}-{next_num}.jpg"
            filepath = dir_path / filename
            
            # Сохраняем фото
            cv2.imwrite(str(filepath), frame)
            saved_files.append(str(filepath))
        
        self.update_status(f"Сохранено: {photo_name}-{next_num}.jpg в обе директории")
        
        # Если папка для просмотра совпадает с одной из директорий, обновляем список
        if self.view_dir and (self.view_dir == self.dir1 or self.view_dir == self.dir2):
            self.load_photos_for_view()
    
    def load_settings(self):
        """Загрузка настроек из файла"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.dir1 = Path(settings['dir1']) if settings.get('dir1') else None
                    self.dir2 = Path(settings['dir2']) if settings.get('dir2') else None
                    self.view_dir = Path(settings['view_dir']) if settings.get('view_dir') else None
            except:
                pass
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        settings = {
            'dir1': str(self.dir1) if self.dir1 else None,
            'dir2': str(self.dir2) if self.dir2 else None,
            'view_dir': str(self.view_dir) if self.view_dir else None
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f)
        
        # Обновляем отображение
        self.dir1_label.config(text=str(self.dir1) if self.dir1 else "Не выбрана", 
                              foreground="black" if self.dir1 else "gray")
        self.dir2_label.config(text=str(self.dir2) if self.dir2 else "Не выбрана",
                              foreground="black" if self.dir2 else "gray")
        self.view_label.config(text=str(self.view_dir) if self.view_dir else "Не выбрана",
                              foreground="black" if self.view_dir else "gray")
        
        messagebox.showinfo("Успех", "Настройки сохранены!")
        
        # Загружаем фото для просмотра если выбрана папка
        if self.view_dir:
            self.load_photos_for_view()
    
    def update_status(self, message):
        """Обновление статуса"""
        self.status_label.config(text=f"Статус: {message}")
    
    def on_closing(self):
        """Закрытие приложения"""
        self.is_recording = False
        if self.cap:
            self.cap.release()
        self.save_settings()
        self.root.destroy()


def main():
    """Главная функция"""
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()