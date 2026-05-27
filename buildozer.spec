[app]

title = Bye Bye DPI
package.name = byebyedpi
package.domain = org.byebye
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0
requirements = python3,kivy,requests,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 30
android.minapi = 21
android.ndk = 23c
android.sdk = 30
android.accept_sdk_license = True
android.gradle_dependencies = 'com.google.android.gms:play-services-vision:20.1.3'
log_level = 2
