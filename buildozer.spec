# buildozer.spec - файл конфигурации сборки (скопируйте целиком)

[app]

title = Bye Bye DPI
package.name = byebyedpi
package.domain = org.byebye
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 2.0
requirements = python3,kivy,requests,opencv-python-headless,numpy
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.arch = arm64-v8a
android.accept_sdk_license = True
