pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "."

ColumnLayout {
    id: root

    property var style: ({})
    property bool karaokeEnabled: false
    property int maximumOutline: 20
    // Subtitle-only: font picker, size and the rounded caption box with its lock.
    property bool backgroundEnabled: false
    readonly property bool boxLocked: root.backgroundEnabled && AppController.subtitleBoxLocked
    readonly property real boxOpacity: Number(root.style.background_opacity_percent || 0)
    readonly property real boxRadius: Number(root.style.background_radius_percent === undefined
        ? 50 : root.style.background_radius_percent)
    signal changeRequested(var patch)

    spacing: Theme.space16

    StyleSection {
        title: qsTr("Phông chữ")
        visible: root.backgroundEnabled

        AppComboBox {
            objectName: "subtitleFontCombo"
            Layout.fillWidth: true
            enabled: !root.boxLocked
            model: AppController.subtitleFontChoices
            textRole: "label"
            currentIndex: {
                const family = String(root.style.font_family || "");
                const choices = AppController.subtitleFontChoices;
                for (let i = 0; i < choices.length; ++i)
                    if (choices[i].family === family) return i;
                return 0;
            }
            onActivated: function(index) {
                root.changeRequested({ "font_family": AppController.subtitleFontChoices[index].family })
            }
        }

        StyleSliderRow {
            label: qsTr("Cỡ chữ")
            sliderObjectName: "subtitleFontSizeSlider"
            suffix: " px"
            from: 10
            to: 240
            value: Number(root.style.font_size || 60)
            onMoved: function(value) { root.changeRequested({ "font_size": value }) }
        }
    }

    StyleSection {
        title: qsTr("Kiểu chữ")

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space16
            AppCheckBox {
                objectName: "compactBoldToggle"
                text: qsTr("Đậm")
                checked: Number(root.style.font_weight || 400) >= 600
                onToggled: root.changeRequested({ "font_weight": checked ? 700 : 400 })
            }
            AppCheckBox {
                objectName: "compactItalicToggle"
                text: qsTr("Nghiêng")
                checked: Boolean(root.style.italic)
                onToggled: root.changeRequested({ "italic": checked })
            }
            Item { Layout.fillWidth: true }
        }

        TextColorStrip {
            objectName: "subtitleTextColorStrip"
            Layout.fillWidth: true
            label: qsTr("Màu chữ")
            selectedColor: String(root.style.text_color || "#FFFFFF")
            onColorSelected: function(value) { root.changeRequested({ "text_color": value }) }
        }

        TextColorStrip {
            objectName: "subtitleKaraokeColorStrip"
            Layout.fillWidth: true
            visible: root.karaokeEnabled
            label: qsTr("Màu karaoke")
            selectedColor: String(root.style.karaoke_color || "#FFEF00")
            onColorSelected: function(value) { root.changeRequested({ "karaoke_color": value }) }
        }
    }

    StyleSection {
        title: qsTr("Viền chữ")

        StyleSliderRow {
            label: qsTr("Độ dày viền")
            sliderObjectName: "compactOutlineWidth"
            suffix: " px"
            from: 0
            to: root.maximumOutline
            value: Number(root.style.outline_width || 0)
            onMoved: function(value) { root.changeRequested({ "outline_width": value }) }
        }

        TextColorStrip {
            objectName: "subtitleOutlineColorStrip"
            Layout.fillWidth: true
            visible: root.karaokeEnabled
            label: qsTr("Màu viền")
            colors: ["#000000", "#FFFFFF", "#4A2516"]
            selectedColor: String(root.style.outline_color || "#000000")
            onColorSelected: function(value) { root.changeRequested({ "outline_color": value }) }
        }
    }

    StyleSection {
        title: qsTr("Khung nền")
        visible: root.backgroundEnabled

        TextColorStrip {
            objectName: "subtitleBackgroundColorStrip"
            Layout.fillWidth: true
            enabled: !root.boxLocked
            label: qsTr("Màu khung")
            colors: ["#000000", "#FFFFFF", "#FFD400", "#EF5350", "#42A5F5", "#66BB6A"]
            selectedColor: String(root.style.background_color || "#000000")
            onColorSelected: function(value) { root.changeRequested({ "background_color": value }) }
        }

        StyleSliderRow {
            label: qsTr("Độ đậm khung")
            sliderObjectName: "subtitleBackgroundOpacity"
            enabled: !root.boxLocked
            value: root.boxOpacity
            onMoved: function(value) { root.changeRequested({ "background_opacity_percent": value }) }
        }

        StyleSliderRow {
            label: qsTr("Bo tròn góc")
            sliderObjectName: "subtitleBackgroundRadius"
            enabled: !root.boxLocked
            value: root.boxRadius
            onMoved: function(value) { root.changeRequested({ "background_radius_percent": value }) }
        }

        AppCheckBox {
            objectName: "subtitleBoxLockToggle"
            Layout.fillWidth: true
            text: qsTr("Khóa phông & khung cho video sau")
            checked: root.boxLocked
            onToggled: AppController.setSubtitleBoxLocked(checked, {
                "background_color": String(root.style.background_color || "#000000"),
                "background_opacity_percent": root.boxOpacity,
                "background_radius_percent": root.boxRadius,
                "font_family": String(root.style.font_family || "Bangers")
            })
        }
    }
}
