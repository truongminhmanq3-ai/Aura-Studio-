import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

// Whole-channel download for Weibo: Weibo does not let an app read a channel's post list without login,
// so the user collects the post links in their own logged-in browser and pastes them here.
AppSurface {
    id: root
    objectName: "weiboChannelGuide"

    property var downloader
    property var parsed: ({ "count": 0, "duplicates": 0, "rejected": [], "truncated": false })
    property bool copied: false

    // Runs in the user's own browser console: reads the post and video links already on the page, copies them.
    readonly property string collectorScript: "(()=>{const m=new Map();document.querySelectorAll('a[href]').forEach(a=>{const h=a.href;let r=h.match(/\\/(?:[0-9]+|status|detail)\\/([A-Za-z0-9]+)/i);if(r&&!m.has(r[1])&&!['home','hot','message','fav','u','login','setting','video'].includes(r[1])){m.set(r[1],'https://m.weibo.cn/detail/'+r[1]);return;}r=h.match(/\\/(?:tv\\/)?show(?:\\/|\\?fid=|\\?.*&fid=)(\\d+:)?([A-Za-z0-9]+)/i);if(r&&!m.has(r[2])){m.set(r[2],'https://video.weibo.com/show?fid='+(r[1]||'')+r[2]);return;}});const t=[...m.values()].join('\\n');navigator.clipboard.writeText(t).then(()=>alert('Đã sao chép '+m.size+' link bài viết Weibo'),()=>prompt('Sao chép thủ công',t))})()"

    readonly property var steps: [
        qsTr("Mở Chrome hoặc Safari trên máy tính, vào weibo.com và đăng nhập tài khoản của bạn."),
        qsTr("Mở trang cá nhân (kênh) cần tải, tab “Video” (hoặc tab “微博 / Bài viết”)."),
        qsTr("Cuộn xuống từ từ cho đến khi hiện đủ các bài bạn muốn tải. Trang chỉ nạp thêm bài khi bạn cuộn, nên hãy chờ vài giây sau mỗi lần cuộn."),
        qsTr("Mở Console của trình duyệt. Chrome: bấm Cmd+Option+J (Mac) hoặc F12 rồi chọn tab Console. Safari: bật menu Phát triển (Cài đặt → Nâng cao → “Hiển thị menu Phát triển”) rồi bấm Cmd+Option+C."),
        qsTr("Bấm “Sao chép đoạn mã” bên dưới, dán vào Console rồi bấm Enter. Chrome có thể yêu cầu gõ allow pasting rồi Enter trước khi cho dán."),
        qsTr("Trình duyệt báo “Đã sao chép N link bài viết Weibo”. Quay lại Aura và dán vào ô “Danh sách link bài Weibo” bên dưới."),
        qsTr("Bấm “Tải tất cả”. Aura bỏ link trùng và video đã tải, bỏ qua bài chỉ có ảnh/chữ, rồi tải lần lượt.")
    ]

    padding: Theme.space16

    SectionHeader {
        Layout.fillWidth: true
        title: qsTr("Tải cả kênh Weibo")
    }

    Text {
        Layout.fillWidth: true
        text: qsTr("Weibo không cho ứng dụng tự đọc danh sách bài của một tài khoản nếu không có phiên đăng nhập. Bạn lấy link bài từ trình duyệt của chính bạn (đã đăng nhập) rồi dán vào đây; Aura lo phần còn lại. Làm theo các bước sau:")
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }

    Repeater {
        model: root.steps
        delegate: RowLayout {
            required property int index
            required property string modelData
            Layout.fillWidth: true
            spacing: Theme.space8
            Text {
                Layout.alignment: Qt.AlignTop
                text: (index + 1) + "."
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.caption
                font.weight: Font.DemiBold
                textFormat: Text.PlainText
            }
            Text {
                Layout.fillWidth: true
                text: modelData
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.caption
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
        }
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: 96
        AppTextArea {
            id: scriptBox
            objectName: "weiboCollectorScript"
            text: root.collectorScript
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.WrapAnywhere
            font.family: "Menlo"
            font.pixelSize: Theme.caption
            accessibleName: qsTr("Đoạn mã lấy link kênh Weibo")
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space8
        StudioButton {
            objectName: "weiboCopyScript"
            text: qsTr("Sao chép đoạn mã")
            variant: "secondary"
            onClicked: {
                AppController.copyText(root.collectorScript);
                root.copied = true;
                copiedTimer.restart();
            }
        }
        Text {
            visible: root.copied
            text: qsTr("Đã sao chép đoạn mã. Dán vào Console của trình duyệt.")
            color: Theme.success
            font.family: Theme.fontFamily
            font.pixelSize: Theme.caption
            textFormat: Text.PlainText
        }
        Item { Layout.fillWidth: true }
        Timer { id: copiedTimer; interval: 3500; onTriggered: root.copied = false }
    }

    Text {
        Layout.fillWidth: true
        text: qsTr("Lưu ý: bài viết chỉ có chữ/ảnh hoặc đã xóa sẽ được bỏ qua. Kênh có bài mới thì lặp lại các bước; video đã tải được tự động bỏ qua không tải lại. Nếu trình duyệt báo đã sao chép 0 link, hãy cuộn thêm trang cho bài viết nạp ra rồi chạy lại đoạn mã.")
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }

    Text {
        Layout.fillWidth: true
        text: qsTr("Danh sách link bài Weibo")
        color: Theme.text
        font.family: Theme.fontFamily
        font.pixelSize: TypeScale.control
        font.weight: Font.DemiBold
        textFormat: Text.PlainText
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: 150
        enabled: Boolean(root.downloader && !root.downloader.batchActive)
        AppTextArea {
            id: pasted
            objectName: "weiboLinks"
            placeholderText: qsTr("Dán các link bài hoặc video Weibo vào đây (tối đa 500 link một lần)")
            accessibleName: qsTr("Danh sách link bài Weibo")
            onTextChanged: root.parsed = root.downloader ? root.downloader.previewLinkBatch(text) : ({ "count": 0, "duplicates": 0, "rejected": [], "truncated": false })
        }
    }

    Text {
        Layout.fillWidth: true
        visible: pasted.text.trim().length > 0
        text: root.parsed.count > 0
            ? qsTr("Tìm thấy %1 link hợp lệ").arg(root.parsed.count)
                + (root.parsed.duplicates > 0 ? qsTr(" · bỏ %1 link trùng").arg(root.parsed.duplicates) : "")
                + (root.parsed.rejected.length > 0 ? qsTr(" · %1 link không hỗ trợ").arg(root.parsed.rejected.length) : "")
                + (root.parsed.truncated ? qsTr(" · chỉ lấy 500 link đầu") : "")
            : qsTr("Chưa thấy link bài hợp lệ nào.")
        color: root.parsed.count > 0 ? Theme.success : Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }

    Text {
        Layout.fillWidth: true
        visible: Boolean(root.downloader && root.downloader.videoOutputDirectory.length > 0)
        text: qsTr("Lưu vào: %1").arg(root.downloader ? root.downloader.videoOutputDirectory : "")
        color: Theme.textMuted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        elide: Text.ElideMiddle
        textFormat: Text.PlainText
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space8
        Text {
            Layout.fillWidth: true
            text: root.downloader ? root.downloader.batchSummary : ""
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: TypeScale.control
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
        }
        StudioButton {
            visible: Boolean(root.downloader && root.downloader.batchActive)
            text: qsTr("Hủy")
            variant: "danger"
            onClicked: if (root.downloader) root.downloader.cancel()
        }
        StudioButton {
            objectName: "weiboDownloadAll"
            text: qsTr("Tải tất cả (%1)").arg(root.parsed.count)
            variant: "primary"
            enabled: root.parsed.count > 0 && Boolean(root.downloader && !root.downloader.hasWork)
                && Boolean(root.downloader && root.downloader.videoOutputDirectory.length > 0)
            onClicked: if (root.downloader) root.downloader.downloadVideoBatch(pasted.text)
        }
    }

    Text {
        Layout.fillWidth: true
        visible: Boolean(root.downloader && root.downloader.batchStoppedReason.length > 0 && !root.downloader.batchActive)
        text: root.downloader && root.downloader.batchStoppedReason === "Cancelled"
            ? qsTr("Đã hủy. Các link chưa tải nằm trong danh sách ở trên.")
            : qsTr("Weibo không trả dữ liệu video hoặc bị hạn chế kết nối nên app đã dừng để không bị chặn thêm. Thử lại sau hoặc lấy lại link mới từ trình duyệt.")
        color: Theme.warning
        font.family: Theme.fontFamily
        font.pixelSize: Theme.caption
        wrapMode: Text.WordWrap
        textFormat: Text.PlainText
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: Boolean(root.downloader && root.downloader.batchFailures.length > 0)
        spacing: Theme.space4
        Repeater {
            model: root.downloader ? root.downloader.batchFailures : []
            delegate: Text {
                required property var modelData
                Layout.fillWidth: true
                text: modelData.url + " — " + I18n.runtimeStatus(modelData.reason)
                color: Theme.danger
                font.family: Theme.fontFamily
                font.pixelSize: Theme.caption
                elide: Text.ElideMiddle
                textFormat: Text.PlainText
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        visible: Boolean(root.downloader && root.downloader.batchExistingCount > 0 && !root.downloader.batchActive)
        spacing: Theme.space8
        Text {
            Layout.fillWidth: true
            text: qsTr("%1 link đã được tải trước đó nên đã bị bỏ qua.").arg(root.downloader ? root.downloader.batchExistingCount : 0)
            color: Theme.textMuted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.caption
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
        }
        StudioButton {
            text: qsTr("Tải lại các video đã có")
            variant: "secondary"
            enabled: Boolean(root.downloader && !root.downloader.hasWork)
            onClicked: if (root.downloader) root.downloader.redownloadBatchExisting()
        }
    }
}
