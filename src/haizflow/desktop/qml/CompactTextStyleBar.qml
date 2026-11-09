pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import "."

ColumnLayout {
    id: root

    property var style: ({})
    property bool karaokeEnabled: false
    property int maximumOutline: 20
    // Subtitle-only: font picker and the rounded caption box with its lock.
    property bool backgroundEnabled: false
    readonly property bool boxLocked: root.backgroundEnabled && AppController.subtitleBoxLocked
    signal changeRequested(var patch)

    spacing: Theme.space12

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space8
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

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.space8

        SettingLabel {
            Layout.fillWidth: true
            text: qsTr("Viền")
        }
        NumericField {
            objectName: "compactOutlineWidth"
            from: 0
            to: root.maximumOutline
            value: Math.round(Number(root.style.outline_width || 0))
            suffix: " px"
            onValueModified: root.changeRequested({ "outline_width": value })
        }
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

    ColumnLayout {
        Layout.fillWidth: true
        visible: root.backgroundEnabled
        spacing: Theme.space8

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space8
            SettingLabel {
                Layout.fillWidth: true
                text: qsTr("Phông chữ")
            }
            AppComboBox {
                objectName: "subtitleFontCombo"
                Layout.preferredWidth: 190
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
        }

        TextColorStrip {
            objectName: "subtitleBackgroundColorStrip"
            Layout.fillWidth: true
            enabled: !root.boxLocked
            label: qsTr("Màu khung nền")
            colors: ["#000000", "#FFFFFF", "#FFD400", "#EF5350", "#42A5F5", "#66BB6A"]
            selectedColor: String(root.style.background_color || "#000000")
            onColorSelected: function(value) { root.changeRequested({ "background_color": value }) }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space8
            SettingLabel {
                Layout.preferredWidth: 96
                text: qsTr("Độ đậm khung")
            }
            AppSlider {
                objectName: "subtitleBackgroundOpacity"
                Layout.fillWidth: true
                enabled: !root.boxLocked
                from: 0
                to: 100
                stepSize: 1
                value: Number(root.style.background_opacity_percent || 0)
                onMoved: root.changeRequested({ "background_opacity_percent": Math.round(value) })
            }
            SettingLabel {
                Layout.preferredWidth: 40
                text: Math.round(Number(root.style.background_opacity_percent || 0)) + "%"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space8
            SettingLabel {
                Layout.preferredWidth: 96
                text: qsTr("Bo tròn")
            }
            AppSlider {
                objectName: "subtitleBackgroundRadius"
                Layout.fillWidth: true
                enabled: !root.boxLocked
                from: 0
                to: 100
                stepSize: 1
                value: Number(root.style.background_radius_percent === undefined
                    ? 50 : root.style.background_radius_percent)
                onMoved: root.changeRequested({ "background_radius_percent": Math.round(value) })
            }
            SettingLabel {
                Layout.preferredWidth: 40
                text: Math.round(Number(root.style.background_radius_percent === undefined
                    ? 50 : root.style.background_radius_percent)) + "%"
            }
        }

        AppCheckBox {
            objectName: "subtitleBoxLockToggle"
            text: qsTr("Khóa khung và phông chữ cho các video sau")
            checked: root.boxLocked
            onToggled: AppController.setSubtitleBoxLocked(checked, {
                "background_color": String(root.style.background_color || "#000000"),
                "background_opacity_percent": Number(root.style.background_opacity_percent || 0),
                "background_radius_percent": Number(root.style.background_radius_percent === undefined
                    ? 50 : root.style.background_radius_percent),
                "font_family": String(root.style.font_family || "Bangers")
            })
        }
    }
}
