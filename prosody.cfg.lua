admins = {}
modules_enabled = {
    "roster";
    "saslauth";
    "disco";
    "private";
    "vcard4";
    "vcard_legacy";
    "version";
    "uptime";
    "time";
    "ping";
    "pep";
    "register";
    "admin_adhoc";
}

allow_registration = true
c2s_require_encryption = false
allow_unencrypted_plain_auth = true
authentication = "internal_plain"
storage = "internal"
log = { { levels = { min = "info" }, to = "console" } }

VirtualHost "localhost"
    allow_registration = true
    c2s_require_encryption = false
    allow_unencrypted_plain_auth = true
