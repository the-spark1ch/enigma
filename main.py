import os
import sys

try:
    import webview
except ImportError:
    print("Error: pywebview library is not installed.")
    print("Install it using: pip install pywebview")
    sys.exit(1)

from engine import PrivacyEngineAPI

def get_resource_path(filename: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def main():
    html_file = get_resource_path("index.html")
    api = PrivacyEngineAPI()

    window = webview.create_window(
        title="ENIGMA // System Hardening & Privacy Shield",
        url=html_file,
        js_api=api,
        width=1240,
        height=880,
        min_size=(960, 680),
        background_color="#000000"
    )

    webview.start(debug=False)

if __name__ == "__main__":
    main()
