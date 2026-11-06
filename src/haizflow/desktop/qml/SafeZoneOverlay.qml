pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "."

Item {
    id: root

    property rect videoRect: Qt.rect(0, 0, 0, 0)
    property string preset: "all" // "none", "all", "tiktok", "reels", "shorts"
    property bool showLabels: true

    readonly property bool active: preset !== "none" && videoRect.width > 0 && videoRect.height > 0

    readonly property bool isVertical: videoRect.height > videoRect.width

    // Percentages based on platform specs for vertical videos, or standard title-safe for landscape
    readonly property real topPercent: {
        if (!isVertical) return 0.05;
        switch (preset) {
        case "tiktok": return 0.15;
        case "reels": return 0.20;
        case "shorts": return 0.10;
        case "all": return 0.20;
        default: return 0.0;
        }
    }

    readonly property real bottomPercent: {
        if (!isVertical) return 0.05;
        switch (preset) {
        case "tiktok": return 0.25;
        case "reels": return 0.35;
        case "shorts": return 0.22;
        case "all": return 0.35;
        default: return 0.0;
        }
    }

    readonly property real rightPercent: {
        if (!isVertical) return 0.05;
        switch (preset) {
        case "tiktok": return 0.20;
        case "reels": return 0.15;
        case "shorts": return 0.16;
        case "all": return 0.20;
        default: return 0.0;
        }
    }

    readonly property real leftPercent: isVertical ? (preset === "all" ? 0.04 : 0.02) : 0.05

    readonly property string presetName: {
        if (!isVertical) return qsTr("Chuẩn 16:9 Title Safe");
        switch (preset) {
        case "tiktok": return "TikTok (9:16)";
        case "reels": return "Facebook / IG Reels (9:16)";
        case "shorts": return "YouTube Shorts (9:16)";
        case "all": return "An toàn chung (All-in-One)";
        default: return "";
        }
    }

    visible: active
    anchors.fill: parent

    // Unsafe Top Area
    Rectangle {
        x: root.videoRect.x
        y: root.videoRect.y
        width: root.videoRect.width
        height: Math.round(root.videoRect.height * root.topPercent)
        color: "#28FF3B30"
        border.width: 1
        border.color: "#80FF3B30"

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: "#CCFF3B30"
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: 4
            height: 16
            radius: 8
            color: "#CC000000"
            visible: root.showLabels && parent.height >= 20
            implicitWidth: topLabel.implicitWidth + 12

            Text {
                id: topLabel
                anchors.centerIn: parent
                text: qsTr("Top UI (Header / Search / Live)")
                color: "#FF8A80"
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.bold: true
            }
        }
    }

    // Unsafe Bottom Area
    Rectangle {
        x: root.videoRect.x
        y: root.videoRect.y + Math.round(root.videoRect.height * (1.0 - root.bottomPercent))
        width: root.videoRect.width
        height: Math.round(root.videoRect.height * root.bottomPercent)
        color: "#28FF3B30"
        border.width: 1
        border.color: "#80FF3B30"

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: "#CCFF3B30"
        }

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.margins: 4
            height: 16
            radius: 8
            color: "#CC000000"
            visible: root.showLabels && parent.height >= 20
            implicitWidth: bottomLabel.implicitWidth + 12

            Text {
                id: bottomLabel
                anchors.centerIn: parent
                text: qsTr("Bottom UI (Caption / Audio / Shop / Actions)")
                color: "#FF8A80"
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.bold: true
            }
        }
    }

    // Unsafe Right Area (Interactive Action Column: Like, Share, Comments)
    Rectangle {
        x: root.videoRect.x + Math.round(root.videoRect.width * (1.0 - root.rightPercent))
        y: root.videoRect.y + Math.round(root.videoRect.height * root.topPercent)
        width: Math.round(root.videoRect.width * root.rightPercent)
        height: Math.round(root.videoRect.height * (1.0 - root.topPercent - root.bottomPercent))
        color: "#24FF9500"
        border.width: 1
        border.color: "#80FF9500"

        Rectangle {
            anchors.centerIn: parent
            rotation: -90
            height: 16
            radius: 8
            color: "#CC000000"
            visible: root.showLabels && parent.width >= 24 && parent.height >= 60
            implicitWidth: rightLabel.implicitWidth + 12

            Text {
                id: rightLabel
                anchors.centerIn: parent
                text: qsTr("Nút Like / Share / Comment")
                color: "#FFD180"
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.bold: true
            }
        }
    }

    // Safe Center Area Box
    Rectangle {
        x: root.videoRect.x + Math.round(root.videoRect.width * root.leftPercent)
        y: root.videoRect.y + Math.round(root.videoRect.height * root.topPercent)
        width: Math.round(root.videoRect.width * (1.0 - root.leftPercent - root.rightPercent))
        height: Math.round(root.videoRect.height * (1.0 - root.topPercent - root.bottomPercent))
        color: "transparent"
        border.width: 1.5
        border.color: "#8000E5FF"
        radius: 4

        // Safe Zone badge in top-left of safe zone
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.margins: 4
            height: 18
            radius: 9
            color: "#CC000000"
            border.width: 1
            border.color: "#8000E5FF"
            visible: root.showLabels
            implicitWidth: safeLabel.implicitWidth + 14

            Text {
                id: safeLabel
                anchors.centerIn: parent
                text: qsTr("Vùng an toàn: %1").arg(root.presetName)
                color: "#00E5FF"
                font.family: Theme.fontFamily
                font.pixelSize: 9
                font.bold: true
            }
        }

        // Golden Subtitle Guideline (Y ≈ 70% of video)
        Item {
            // Position relative to safe box: video height * 0.70 minus safe box top
            readonly property real targetY: (root.videoRect.height * 0.70) - (root.videoRect.height * root.topPercent)
            anchors.left: parent.left
            anchors.right: parent.right
            y: Math.max(0, Math.min(parent.height - 1, targetY))
            height: 1
            visible: targetY >= 0 && targetY <= parent.height

            Rectangle {
                anchors.fill: parent
                color: "#9934C759"
            }

            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.top
                anchors.bottomMargin: 2
                anchors.rightMargin: 6
                height: 14
                radius: 7
                color: "#CC000000"
                border.width: 0.5
                border.color: "#34C759"
                implicitWidth: goldenLabel.implicitWidth + 8

                Text {
                    id: goldenLabel
                    anchors.centerIn: parent
                    text: qsTr("Vị trí vàng phụ đề (Y ≈ 70%)")
                    color: "#34C759"
                    font.family: Theme.fontFamily
                    font.pixelSize: 8
                    font.bold: true
                }
            }
        }
    }
}
