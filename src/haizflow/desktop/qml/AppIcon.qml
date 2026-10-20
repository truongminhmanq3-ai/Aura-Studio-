import QtQuick
import "."

Item {
    id: root

    property string glyph: ""
    property color iconColor: Theme.textMuted
    property int iconSize: Theme.icon
    property int horizontalAlignment: Text.AlignHCenter
    property int verticalAlignment: Text.AlignVCenter

    implicitWidth: iconSize + 4
    implicitHeight: iconSize + 4
    Accessible.ignored: true

    readonly property bool isCanvasVector: glyph === "\uE80F"
        || glyph === "\uE72B"
        || glyph === "\uE72A"
        || glyph === "\uE76C"
        || glyph === "\uE70D"
        || glyph === "\uE70E"
        || glyph === "\uE710"
        || glyph === "\uE8A3"
        || glyph === "\uE738"
        || glyph === "\uE71F"
        || glyph === "\uE711"
        || glyph === "\uE721"
        || glyph === "\uE73E"
        || glyph === "\uE896"
        || glyph === "\uE898"

    onGlyphChanged: iconCanvas.requestPaint()
    onIconColorChanged: iconCanvas.requestPaint()
    onIconSizeChanged: iconCanvas.requestPaint()

    Canvas {
        id: iconCanvas
        anchors.centerIn: parent
        width: Math.max(16, root.iconSize + 2)
        height: Math.max(16, root.iconSize + 2)
        visible: root.isCanvasVector
        antialiasing: true

        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var w = width;
            var h = height;
            var cx = w / 2.0;
            var cy = h / 2.0;
            var s = root.iconSize;

            ctx.strokeStyle = root.iconColor.toString();
            ctx.fillStyle = root.iconColor.toString();
            ctx.lineWidth = Math.max(1.5, s * 0.115);
            ctx.lineCap = "round";
            ctx.lineJoin = "round";

            if (root.glyph === "\uE80F") {
                // Apple SF-Symbols clean minimalist Home icon
                var hw = s * 0.44;
                var topY = cy - s * 0.40;
                var eaveY = cy - s * 0.03;
                var botY = cy + s * 0.38;
                var bodyW = s * 0.33;

                // Roof chevron
                ctx.beginPath();
                ctx.moveTo(cx - hw, eaveY);
                ctx.lineTo(cx, topY);
                ctx.lineTo(cx + hw, eaveY);
                ctx.stroke();

                // House walls + rounded bottom corners
                ctx.beginPath();
                ctx.moveTo(cx - bodyW, eaveY - s * 0.04);
                ctx.lineTo(cx - bodyW, botY);
                ctx.lineTo(cx + bodyW, botY);
                ctx.lineTo(cx + bodyW, eaveY - s * 0.04);
                ctx.stroke();
            } else if (root.glyph === "\uE72B") {
                // Crisp Chevron Left (<)
                var dx = s * 0.19;
                var dy = s * 0.34;
                ctx.beginPath();
                ctx.moveTo(cx + dx * 0.85, cy - dy);
                ctx.lineTo(cx - dx * 1.15, cy);
                ctx.lineTo(cx + dx * 0.85, cy + dy);
                ctx.stroke();
            } else if (root.glyph === "\uE72A" || root.glyph === "\uE76C") {
                // Crisp Chevron Right (>)
                var rx = s * 0.19;
                var ry = s * 0.34;
                ctx.beginPath();
                ctx.moveTo(cx - rx * 0.85, cy - ry);
                ctx.lineTo(cx + rx * 1.15, cy);
                ctx.lineTo(cx - rx * 0.85, cy + ry);
                ctx.stroke();
            } else if (root.glyph === "\uE70D") {
                // Crisp Chevron Down (v)
                var vx = s * 0.30;
                var vy = s * 0.16;
                ctx.beginPath();
                ctx.moveTo(cx - vx, cy - vy * 0.8);
                ctx.lineTo(cx, cy + vy * 1.2);
                ctx.lineTo(cx + vx, cy - vy * 0.8);
                ctx.stroke();
            } else if (root.glyph === "\uE70E") {
                // Crisp Chevron Up (^)
                var ux = s * 0.30;
                var uy = s * 0.16;
                ctx.beginPath();
                ctx.moveTo(cx - ux, cy + uy * 0.8);
                ctx.lineTo(cx, cy - uy * 1.2);
                ctx.lineTo(cx + ux, cy + uy * 0.8);
                ctx.stroke();
            } else if (root.glyph === "\uE710" || root.glyph === "\uE8A3") {
                // Crisp Plus (+)
                var pr = s * 0.34;
                ctx.beginPath();
                ctx.moveTo(cx - pr, cy);
                ctx.lineTo(cx + pr, cy);
                ctx.moveTo(cx, cy - pr);
                ctx.lineTo(cx, cy + pr);
                ctx.stroke();
            } else if (root.glyph === "\uE738" || root.glyph === "\uE71F") {
                // Crisp Minus (-)
                var mr = s * 0.34;
                ctx.beginPath();
                ctx.moveTo(cx - mr, cy);
                ctx.lineTo(cx + mr, cy);
                ctx.stroke();
            } else if (root.glyph === "\uE711") {
                // Crisp Close (X)
                var xr = s * 0.28;
                ctx.beginPath();
                ctx.moveTo(cx - xr, cy - xr);
                ctx.lineTo(cx + xr, cy + xr);
                ctx.moveTo(cx + xr, cy - xr);
                ctx.lineTo(cx - xr, cy + xr);
                ctx.stroke();
            } else if (root.glyph === "\uE721") {
                // Crisp Search Magnifier
                var sr = s * 0.26;
                var scx = cx - s * 0.06;
                var scy = cy - s * 0.06;
                ctx.beginPath();
                ctx.arc(scx, scy, sr, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(scx + sr * 0.72, scy + sr * 0.72);
                ctx.lineTo(cx + s * 0.34, cy + s * 0.34);
                ctx.stroke();
            } else if (root.glyph === "\uE73E") {
                // Crisp Checkmark
                ctx.beginPath();
                ctx.moveTo(cx - s * 0.32, cy + s * 0.02);
                ctx.lineTo(cx - s * 0.08, cy + s * 0.26);
                ctx.lineTo(cx + s * 0.34, cy - s * 0.22);
                ctx.stroke();
            } else if (root.glyph === "\uE896" || root.glyph === "\uE898") {
                // Crisp Download Arrow
                ctx.beginPath();
                ctx.moveTo(cx, cy - s * 0.36);
                ctx.lineTo(cx, cy + s * 0.22);
                ctx.moveTo(cx - s * 0.24, cy + s * 0.0);
                ctx.lineTo(cx, cy + s * 0.24);
                ctx.lineTo(cx + s * 0.24, cy + s * 0.0);
                ctx.moveTo(cx - s * 0.32, cy + s * 0.38);
                ctx.lineTo(cx + s * 0.32, cy + s * 0.38);
                ctx.stroke();
            }
        }
    }

    function resolveGlyph(code) {
        switch (code) {
        case "\uE712": return "⋯"
        case "\uE768": return "▶"
        case "\uE769": return "⏸"
        case "\uE71A": return "■"
        case "\uE72C": return "↻"
        case "\uE777": return "↺"
        case "\uE74D": return "⌫"
        case "\uE70F": return "✎"
        case "\uE713": return "⚙"
        case "\uE8B7": return "❐"
        case "\uE8A7": return "↗"
        case "\uE789": return "↗"
        case "\uE71B": return "🔗"
        case "\uE8C8": return "⧉"
        case "\uE77F": return "📋"
        case "\uE714": return "▶"
        case "\uE8D6": return "♪"
        case "\uE767": return "🔊"
        case "\uE74F": return "🔇"
        case "\uE740": return "⤢"
        case "\uE73F": return "⤡"
        case "\uE922": return "⤢"
        case "\uE923": return "⤡"
        case "\uE7A7": return "↶"
        case "\uE7A6": return "↷"
        case "\uE8C6": return "✂"
        case "\uE72E": return "🔒"
        case "\uE785": return "🔓"
        case "\uE892": return "⏮"
        case "\uE893": return "⏭"
        case "\uE946": return "ⓘ"
        case "\uE7BA": return "⚠"
        case "\uEA39": return "⊗"
        default: return code
        }
    }

    Text {
        anchors.fill: parent
        visible: !root.isCanvasVector
        text: root.resolveGlyph(root.glyph)
        color: root.iconColor
        font.family: Theme.iconFont
        font.pixelSize: root.iconSize
        font.weight: Font.Medium
        horizontalAlignment: root.horizontalAlignment
        verticalAlignment: root.verticalAlignment
        textFormat: Text.PlainText
    }
}
