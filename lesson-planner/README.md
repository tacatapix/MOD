# Planejamento de Aula

Aplicativo Android para criação de planos de aula com sugestão automática de códigos BNCC via IA (OpenAI) e exportação em PDF.

## Funcionalidades

- Formulário com todos os campos editáveis de um plano de aula (Identificação, Tema, Objetivos, Conteúdos, Habilidades BNCC, Competências Gerais, Metodologia, Recursos, Avaliação, Referências).
- Geração automática de códigos BNCC e competências gerais via OpenAI (gpt-4o-mini), analisando o componente curricular, ano/série, tema, objetivos, conteúdos e metodologia.
- Exportação do plano em PDF e compartilhamento pelo Android (e-mail, WhatsApp, Google Drive etc.).
- Textos em português do Brasil, com correção ortográfica nativa do teclado Android.
- Chave da API OpenAI armazenada localmente no dispositivo via DataStore (tela de Ajustes).

## Como compilar

Pré-requisitos: JDK 17, Android SDK 34, Gradle wrapper (incluso).

```bash
./gradlew assembleDebug
```

O APK será gerado em `app/build/outputs/apk/debug/app-debug.apk`.

## Como usar

1. Instale o APK no seu Android.
2. Abra o app e toque no ícone de engrenagem (Ajustes) para colar sua chave da OpenAI (crie em https://platform.openai.com/api-keys).
3. Preencha os campos do plano de aula.
4. Toque em **Gerar BNCC** para que a IA sugira habilidades e competências gerais com base no conteúdo.
5. Toque em **Exportar PDF** para gerar o arquivo e compartilhar.

## Stack

- Kotlin 2.0 + Jetpack Compose (Material 3)
- OkHttp + kotlinx.serialization para integração com OpenAI
- android.graphics.pdf.PdfDocument (nativo) para geração de PDF
- AndroidX DataStore Preferences para persistência da chave da API
