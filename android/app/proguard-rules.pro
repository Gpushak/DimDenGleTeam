# Правила R8/ProGuard для release-сборки.
# Для debug-сборки minifyEnabled=false, поэтому файл нужен лишь как заглушка,
# чтобы конфигурация release не падала на отсутствующем файле.

# Модели API разбираются через Gson по именам полей — имена нельзя переименовывать.
-keepclassmembers class com.example.warehouse.data.model.** {
    <fields>;
    <init>();
}

# Retrofit интерфейсы и их аннотации.
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation

# Retrofit читает значения методов по аннотациям (@GET, @Path, @Query).
-if interface * { @retrofit2.http.* public *** *(...); }
-keep,allowoptimization,allowshrinking,allowobfuscation class <3>

# Модели Gson требуют сохранения generic-сигнатур.
-keep class * extends com.google.gson.reflect.TypeToken
-keep class * implements java.io.Serializable

# ML Kit и CameraX поставляются готовыми, дополнительных правил не требуют.