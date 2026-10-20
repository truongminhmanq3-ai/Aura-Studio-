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
        text: qsTr("DeepSeek · Dịch phụ đề")
        color: Theme.text
        font.pixelSize: TypeScale.title
        font.weight: Font.DemiBold
    }
    Text {
        Layout.fillWidth: true
        text: qsTr("Chọn DeepSeek Flash hoặc DeepSeek V4 Pro ở mục Model dịch trong dự án. Phụ đề sẽ được gửi đến DeepSeek và dùng số dư API của tài khoản. HY-MT2 và Gemini vẫn dùng được.")
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
                objectName: "deepSeekKeyStatus"
                Layout.fillWidth: true
                text: AppController.deepSeekKeyConfigured ? qsTr("Đã lưu API key trên máy") : qsTr("Chưa có API key · Bạn có thể dán sau")
                color: Theme.textMuted
                font.pixelSize: TypeScale.body
            }
            RowLayout {
                Layout.fillWidth: true
                AppTextField {
                    id: keyInput
                    objectName: "deepSeekApiKeyInput"
                    Layout.fillWidth: true
                    accessibleName: qsTr("DeepSeek API key")
                    placeholderText: qsTr("Dán DeepSeek API key")
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
                    objectName: "saveDeepSeekApiKeyButton"
                    text: qsTr("Lưu key")
                    variant: "primary"
                    enabled: keyInput.text.trim().length > 0
                    onClicked: if (AppController.saveDeepSeekApiKey(keyInput.text)) {
                        keyInput.clear(); root.keyVisible = false;
                        root.message = qsTr("Đã lưu vào kho bảo mật. Key sẽ được kiểm tra khi bạn chạy dịch.");
                    }
                }
                StudioButton {
                    text: qsTr("Lấy API key")
                    onClicked: AppController.openDeepSeekApiKeys()
                }
                StudioButton {
                    text: qsTr("Xóa key")
                    enabled: AppController.deepSeekKeyConfigured
                    onClicked: if (AppController.clearDeepSeekApiKey()) root.message = qsTr("Đã xóa key khỏi máy.");
                }
            }
            Text {
                Layout.fillWidth: true
                text: qsTr("Key được lưu trong kho bảo mật của hệ điều hành (Keychain trên Mac), không lưu trong dự án. Lưu key không gửi yêu cầu dịch.")
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
