import os
import sys

try:
    import webview
except ImportError:
    print("Error: pywebview library is not installed.")
    print("Install it using: pip install pywebview")
    sys.exit(1)

from core import PrivacyEngineAPI

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(base_dir, "index.html")

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