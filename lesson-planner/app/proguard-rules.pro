# Keep kotlinx.serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keep,includedescriptorclasses class com.tacatapix.planejamentoaula.**$$serializer { *; }
-keepclassmembers class com.tacatapix.planejamentoaula.** {
    *** Companion;
}
-keepclasseswithmembers class com.tacatapix.planejamentoaula.** {
    kotlinx.serialization.KSerializer serializer(...);
}
