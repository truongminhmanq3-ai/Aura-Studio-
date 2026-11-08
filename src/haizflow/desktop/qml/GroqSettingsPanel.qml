pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import "."

ColumnLayout {
    id: root
    property bool keyVisible: false
    property string message: ""
    spacing: Theme.space16

    Text {
        Layout.fillWidth: true
        text: qsTr("Groq Whisper · Nhận dạng giọng nói siêu tốc")
        color: Theme.text
        font.pixelSize: TypeScale.title
        font.weight: Font.DemiBold
    }

    Text {
        Layout.fillWidth: true
        text: qsTr("Nhận dạng giọng nói bằng mô hình Whisper Large-v3-turbo (1.5 tỷ tham số) qua Groq Cloud với độ trễ chỉ 2-3 giây. Hoàn toàn miễn phí, không tốn dung lượng máy hay VRAM GPU.")
        color: Theme.textMuted
        font.pixelSize: TypeScale.body
        wrapMode: Text.WordWrap
    }

    SettingsGroup {
        Layout.fillWidth: true
        title: qsTr("API key")

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space12

            Text {
                objectName: "groqKeyStatus"
                Layout.fillWidth: true
                text: AppController.groqKeyConfigured ? qsTr("Đã lưu API key trên máy") : qsTr("Chưa có API key · Bạn có thể dán sau")
                color: Theme.textMuted
                font.pixelSize: TypeScale.body
            }

            RowLayout {
                Layout.fillWidth: true

                AppTextField {
                    id: keyInput
                    objectName: "groqApiKeyInput"
                    Layout.fillWidth: true
                    accessibleName: qsTr("Groq API key")
                    placeholderText: qsTr("Dán Groq API key (gsk_...)")
                    echoMode: root.keyVisible ? TextInput.Normal : TextInput.Password
                    inputMethodHints: Qt.ImhHiddenText | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                }

                StudioButton {
                    text: root.keyVisible ? qsTr("Ẩn") : qsTr("Hiện")
                    enabled: keyInput.text.length > 0
                    onClicked: root.keyVisible = !root.keyVisible
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space8

                StudioButton {
                    objectName: "saveGroqApiKeyButton"
                    text: qsTr("Lưu key")
                    variant: "primary"
                    enabled: keyInput.text.trim().length > 0
                    onClicked: if (AppController.saveGroqApiKey(keyInput.text)) {
                        keyInput.clear(); root.keyVisible = false;
                        root.message = qsTr("Đã lưu vào kho bảo mật. Bạn có thể chọn Groq Whisper trong dự án.");
                    }
                }

                StudioButton {
                    text: qsTr("Lấy API key miễn phí")
                    onClicked: AppController.openGroqApiKeys()
                }

                StudioButton {
                    text: qsTr("Xóa key")
                    enabled: AppController.groqKeyConfigured
                    onClicked: if (AppController.clearGroqApiKey()) root.message = qsTr("Đã xóa key khỏi máy.");
                }
            }

            Text {
                Layout.fillWidth: true
                text: qsTr("Key được lưu trong kho bảo mật của hệ điều hành (Keychain trên Mac), không lưu trong dự án. Bạn có thể lấy key miễn phí tại console.groq.com/keys.")
                color: Theme.textSubtle
                font.pixelSize: TypeScale.metadata
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: root.message
                visible: text.length > 0
                color: Theme.textMuted
                font.pixelSize: TypeScale.body
                wrapMode: Text.WordWrap
            }
        }
    }

    onVisibleChanged: if (!visible) { keyInput.clear(); keyVisible = false; message = ""; }
}

