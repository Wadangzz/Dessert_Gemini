import sys
import os
from PySide6.QtWidgets import QApplication
# from cli_gui import InventoryApp
from cli_gui_gemini import InventoryApp

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load stylesheet
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_path, 'style.qss')
        with open(qss_path, 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found. Running with default styles.")
    except Exception as e:
        print(f"Warning: Could not load stylesheet. {e}")

    # Create and show the main window directly
    main_window = InventoryApp()
    main_window.show()
    sys.exit(app.exec())