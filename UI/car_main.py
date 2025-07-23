from PySide6.QtUiTools import loadUiType
from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
import PySide6.QtCore as QtCore
import sys
import os
import pandas as pd
import joblib
import numpy as np
import re
import pyautogui
from car_data import load_structured_car_data
from sklearn.metrics import mean_absolute_error
import resources_rc

ui, _ = loadUiType("clone-dashboard_4.ui")

class FilterComboBox(QComboBox):
    popupAboutToBeShown = Signal()

    def showPopup(self): # 팝업 열기 전에 커스텀 시그널 발생
        self.popupAboutToBeShown.emit()
        super().showPopup()

class DashWindow(QMainWindow, ui):
    ### 1. 생성자 및 초기 설정
    def __init__(self): # UI, 폰트, 데이터, 모델, 콤보박스 초기화
        super(DashWindow, self).__init__()

        # 윈도우 설정: 타이틀바 제거 및 크기 제한
        flags = Qt.WindowFlags(Qt.FramelessWindowHint)
        self.setMaximumSize(1300, 1000)
        self.setWindowFlags(flags)
        self.setupUi(self)
        self.showNormal()
        self.offset = None  # 창 드래그 이동을 위한 변수

        # 폰트 적용 (NanumSquareEB, NanumSquareB)
        font_eb_id = QFontDatabase.addApplicationFont("fonts/NanumSquareEB.ttf")
        font_b_id = QFontDatabase.addApplicationFont("fonts/NanumSquareB.ttf")

        try:
            font_eb = QFontDatabase.applicationFontFamilies(font_eb_id)[0]
            font_b = QFontDatabase.applicationFontFamilies(font_b_id)[0]

            self.label.setFont(QFont(font_eb, 25))
            self.logo_name.setFont(QFont(font_eb, 13))
            self.result.setFont(QFont(font_b, 12))
            self.label_2.setFont(QFont(font_b, 15))
            self.label_4.setFont(QFont(font_b, 13))
            self.label_5.setFont(QFont(font_b, 13))

        except IndexError:
            print("폰트 로딩 실패")

        # 데이터프레임 로딩
        self.df = load_structured_car_data("car_price_remove_one_hot_encoding.csv")  # 필터용
        self.ml_df = pd.read_csv("car_price_remove_one_hot_encoding.csv")  # 예측용

        # 모델 로딩
        with open("car.model", "rb") as f:
            self.ml_model = joblib.load(f)

        # QComboBox 교체 (팝업 시그널 지원)
        self.replace_combobox("year")
        self.replace_combobox("oilingtype")
        self.replace_combobox("mileage")

        # 버튼 시그널 연결
        self.pushButton.clicked.connect(self.close_win)
        self.pushButton_3.clicked.connect(self.minimize_win)
        self.pushButton_2.clicked.connect(self.mini_maximize)
        self.pushButton_4.clicked.connect(self.display_result)

        self.initialize_inputs()  # 초기 입력 필드 설정

        QTimer.singleShot(500, self.switch_to_korean)  # 한글 모드 전환

    def replace_combobox(self, name): # QComboBox를 사용자 정의 FilterComboBox로 교체
        old = self.findChild(QComboBox, name)
        parent_layout = old.parent().layout()
        index = parent_layout.indexOf(old)

        new = FilterComboBox(self)
        new.setObjectName(name)
        parent_layout.insertWidget(index, new)
        old.deleteLater()
        setattr(self, name, new)

    def initialize_inputs(self): # 시그널 연결 및 필터 초기화
        # 시그널 연결
        self.car_name.textChanged.connect(self.update_filters)
        self.year.popupAboutToBeShown.connect(self.update_filters)
        self.oilingtype.popupAboutToBeShown.connect(self.update_filters)
        self.mileage.popupAboutToBeShown.connect(self.update_filters)

        # 필터값 리셋 시 초기화
        self.year.popupAboutToBeShown.connect(lambda: self.reset_if_selected(self.year))
        self.oilingtype.popupAboutToBeShown.connect(lambda: self.reset_if_selected(self.oilingtype))
        self.mileage.popupAboutToBeShown.connect(lambda: self.reset_if_selected(self.mileage))

        self.update_inputs()

    def update_inputs(self): # 차량명 자동완성 + 필터 최초 로딩
        name_list = sorted(self.df['car_name'].unique())
        completer = QCompleter()
        completer.setModel(QStringListModel(name_list))
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.car_name.setCompleter(completer)
        completer.activated[str].connect(self.on_completer_activated)

        self.update_filters()

    def switch_to_korean(self): # 한글 입력 포커스 적용
        self.car_name.setFocus()
        pyautogui.press("hangul")

    ### 2. 필터 및 콤보박스
    def update_filters(self): # 조건에 따른 필터링 및 콤보박스 항목 갱신
        # 현재 선택값 읽기
        car_name = self.car_name.text().strip()
        selected_year = self.year.currentText()
        selected_oil = self.oilingtype.currentText()
        selected_mileage_key = self.mileage.currentData()

        filtered = self.df.copy()  # 원본 복사

        # 조건별 점진적 필터링
        if car_name:
            filtered = filtered[filtered['car_name'].str.contains(car_name, case=False, na=False, regex=False)]
        if selected_year.isdigit():
            filtered = filtered[filtered['year'] == int(selected_year)]
        if selected_oil and selected_oil != "오일타입 선택":
            filtered = filtered[filtered['oilingtype'] == selected_oil]

        # 연식, 오일타입 콤보박스 갱신용 값 추출
        year_list = sorted(filtered['year'].unique())
        oil_list = sorted(filtered['oilingtype'].unique())

        # 주행거리 → 범위별 라벨/키 구성
        mileage_set = set()
        for v in filtered['mileage'].unique():
            try:
                # 문자열 주행거리 전처리
                if isinstance(v, str):
                    if 'mileage_' in v:
                        continue
                    if "~" in v:
                        start_str = v.split("~")[0]
                        val = int(re.sub(r"[^\d]", "", start_str))
                    else:
                        val = int(re.sub(r"[^\d]", "", v))
                else:
                    val = int(v)
                # 범위 설정
                bucket = (val // 10000) * 10000
                start = 0 if bucket == 0 else bucket + 1
                end = bucket + 10000
                if start > 0:
                    label = f"{start - 1:,}~{end:,}km"
                else:
                    label = f"{start:,}~{end:,}km"
                key = f"mileage_{start}_{end}"
                mileage_set.add((label, key))
            except:
                continue

        # 정렬 후 콤보박스 적용
        mileage_list = sorted(mileage_set, key=lambda x: int(x[1].split("_")[1]))

        # 콤보박스 값 설정
        self.update_combobox(self.year, year_list, "연식 선택", selected_year)
        self.update_combobox(self.oilingtype, oil_list, "오일타입 선택", selected_oil)

        self.mileage.blockSignals(True)
        self.mileage.clear()
        self.mileage.addItem("주행거리(km)", userData=None)
        for label, key in mileage_list:
            self.mileage.addItem(label, userData=key)
        # 기존 선택 복원
        if selected_mileage_key:
            index = self.mileage.findData(selected_mileage_key)
            if index != -1:
                self.mileage.setCurrentIndex(index)
            else:
                self.mileage.setCurrentIndex(0)
        else:
            self.mileage.setCurrentIndex(0)
        self.mileage.blockSignals(False)

    def update_combobox(self, combo, values, placeholder, current_value): # 특정 콤보박스 항목 업데이트
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder)
        combo.setItemData(0, 0, Qt.UserRole - 1)
        for v in values:
            combo.addItem(str(v))
        if str(current_value) in [str(v) for v in values]:
            combo.setCurrentText(str(current_value))
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def reset_if_selected(self, combo: QComboBox): # 콤보박스 클릭 시 기존 선택값 초기화
        if combo.currentIndex() > 0:
            combo.setCurrentIndex(0)

    def on_completer_activated(self, text): # 자동완성 선택 시 필터 재적용 (입력창 갱신)
        self.car_name.setText(text)
        self.update_filters()

    ### 3. 검색 및 예측
    def display_result(self): # 예측 실행 및 결과 텍스트 + 이미지 출력
        # 사용자 입력 읽기
        car_name = self.car_name.text().strip()
        year = self.year.currentText()
        oilingtype = self.oilingtype.currentText()
        mileage_str = self.mileage.currentData()

        # 필수 입력값 확인
        if not car_name or not year.isdigit() or oilingtype == "오일타입 선택" or mileage_str is None:
            QMessageBox.warning(self, "검색 오류", "이름과 모든 옵션을 올바르게 입력 또는 선택해주세요.")
            return

        # 주행거리 파싱
        if mileage_str.startswith("mileage_"):
            try:
                _, start, end = mileage_str.split("_")
                mileage_min = int(start)
                mileage_max = int(end)
            except:
                QMessageBox.warning(self, "입력 오류", f"주행거리를 해석할 수 없습니다: {mileage_str}")
                return
        else:
            QMessageBox.warning(self, "입력 오류", f"주행거리를 해석할 수 없습니다: {mileage_str}")
            return

        df = self.ml_df.copy()
        
        # 폰트 적용 (NanumSquareEB, NanumSquareB)
        font_eb_id = QFontDatabase.addApplicationFont("fonts/NanumSquareEB.ttf")
        font_b_id = QFontDatabase.addApplicationFont("fonts/NanumSquareB.ttf")

        try:
            # one-hot 필터링
            if f'car_name{car_name}' in df.columns:
                df = df[df[f'car_name{car_name}'] == 1]
            if f'year_{year}' in df.columns:
                df = df[df[f'year_{year}'] == 1]
            if f'oilingtype_{oilingtype}' in df.columns:
                df = df[df[f'oilingtype_{oilingtype}'] == 1]

            mileage_col = f"mileage_{mileage_min}_{mileage_max}"
            if mileage_col in df.columns:
                df = df[df[mileage_col] == True]
            else:
                QMessageBox.warning(self, "입력 오류", f"{mileage_col} 주행거리 컬럼을 찾을 수 없습니다.")
                return

            if df.empty:
                QMessageBox.information(self, "결과 없음", "해당 조건에 맞는 데이터가 없습니다.")
                return
            
            # 예측
            x = df.drop("price", axis=1)
            y_true = df["price"]
            y_pred = self.ml_model.predict(x)

            # 결과 텍스트 출력
            result_text = f"- 차량 모델 : {car_name}\n" \
                          f"- 연식          : {year}\n" \
                          f"- 오일타입  : {oilingtype}\n" \
                          f"- 주행거리  : {mileage_min - 1} ~ {mileage_max}\n\n" \
                          f"- 최소 가격             : {np.min(y_pred):,.0f}만 원\n" \
                          f"- 최대 가격             : {np.max(y_pred):,.0f}만 원\n" \
                          f"- 평균 가격             : {np.mean(y_pred):,.0f}만 원\n" \
                          f"- MAE(평균 오차)  : {mean_absolute_error(y_true, y_pred):.0f}만 원"
            font_b_id = QFontDatabase.addApplicationFont("fonts/NanumSquareB.ttf")
            font_b = QFontDatabase.applicationFontFamilies(font_b_id)[0]
            self.result.setFont(QFont(font_b, 12))
            self.result.setText(result_text)


        except Exception as e:
            QMessageBox.critical(self, "예측 오류", f"예측 중 오류 발생:\n{str(e)}")

        # 이미지 출력
        image_filename = os.path.join("picture", f"{car_name}.jpg")
        if os.path.exists(image_filename):
            pixmap = QPixmap(image_filename)
            scaled_pixmap = pixmap.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image.setPixmap(scaled_pixmap)
        else:
            self.image.clear()
            QMessageBox.information(self, "이미지 없음", f"{image_filename} 이미지를 찾을 수 없습니다.")

    ### 4. UI 창 조작 및 드래그
    def mousePressEvent(self, event): # 마우스 클릭 → 위치 기억
        if self.topBar.geometry().contains(event.pos()):
            self.offset = event.pos()

    def mouseMoveEvent(self, event): # 드래그 → 창 이동
        if self.offset is not None and event.buttons() == QtCore.Qt.LeftButton:
            self.move(self.pos() + event.pos() - self.offset)

    def mouseReleaseEvent(self, event): # 드래그 끝 → 위치 초기화
        self.offset = None

    def close_win(self): # 종료 버튼
        self.close()

    def mini_maximize(self): # 최소화 버튼
        if self.isMaximized():
            self.pushButton_2.setIcon(QIcon(":/icons/icons/maximize.svg"))
            self.showNormal()
        else:
            self.pushButton_2.setIcon(QIcon(":/icons/icons/minimize.svg"))
            self.showMaximized()

    def minimize_win(self): # 최대화/복원 토글
        self.showMinimized()

# 앱 실행
if __name__ == "__main__":
    app = QApplication()
    window = DashWindow()
    window.show()
    sys.exit(app.exec())