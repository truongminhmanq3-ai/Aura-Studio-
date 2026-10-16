ObjC.import('Foundation');

var SERVICE = 'HaizFlow';
var TARGETS = {
    deepseek: 'HaizFlow/DeepSeek/APIKey',
    elevenlabs: 'HaizFlow/ElevenLabs/APIKey',
    gemini: 'HaizFlow/Gemini/APIKey',
    zernio: 'HaizFlow/Zernio/APIKey'
};

function shellQuote(value) {
    return "'" + value.replace(/'/g, "'\\''") + "'";
}

function writeCredential(service, target, secret) {
    var app = Application.currentApplication();
    app.includeStandardAdditions = true;
    var command = '/usr/bin/security add-generic-password -U -s ' + shellQuote(service)
        + ' -a ' + shellQuote(target) + ' -w ' + shellQuote(secret);
    try { app.doShellScript(command); }
    catch (_) { throw new Error('Keychain không lưu được key. Kiểm tra quyền truy cập Keychain rồi thử lại.'); }
}

function run(args) {
    if (args.length !== 1) throw new Error('Cần đường dẫn file cấu hình key của team.');
    var raw = $.NSString.stringWithContentsOfFileEncodingError($(args[0]), $.NSUTF8StringEncoding, null);
    if (!raw) throw new Error('Không đọc được file cấu hình key.');
    var config;
    try { config = JSON.parse(ObjC.unwrap(raw)); }
    catch (_) { throw new Error('File cấu hình không đúng định dạng JSON.'); }
    if (config.schema !== 1 || !config.providers || typeof config.providers !== 'object') {
        throw new Error('File cấu hình key không hợp lệ.');
    }
    var entries = [];
    Object.keys(config.providers).forEach(function(provider) {
        if (!Object.prototype.hasOwnProperty.call(TARGETS, provider)) {
            throw new Error('Cấu hình có dịch vụ không được hỗ trợ.');
        }
        var key = config.providers[provider];
        if (typeof key !== 'string' || !key.length || key.length > 4096 || /\s/.test(key)) {
            throw new Error('Key không hợp lệ cho ' + provider + '.');
        }
        entries.push([provider, key]);
    });
    if (!entries.length) throw new Error('Cấu hình chưa có key.');
    entries.forEach(function(entry) { writeCredential(SERVICE, TARGETS[entry[0]], entry[1]); });
    return 'Đã nạp key: ' + entries.map(function(entry) { return entry[0]; }).join(', ') + '. Mở lại HaizFlow để dùng.';
}
