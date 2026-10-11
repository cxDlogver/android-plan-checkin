# Isolated TalkBack speech evidence tool

This emulator-only TTS service receives actual Android TalkBack synthesis requests, delegates speech synthesis to the installed official eSpeak engine, then returns that exact PCM through Android's `SynthesisCallback`. It copies WAV/metadata only when the request caller UID belongs to `com.android.talkback`. It does not access or modify the product database, request microphone access, capture host audio, or substitute UI labels for actual TalkBack requests.

Metadata preserves the request text, actual backend/locale, caller UID/packages, PCM format, offered byte count and stop state. Acceptance uses only complete, non-stopped requests, matched with the actual TalkBack focus/action logs and UI hierarchy. A WAV created by a separate scripted speech call is not accepted as evidence.

The tool is packaged separately as `com.xiang.verification.reader`; it is never part of the product APK. Android API contracts: [TextToSpeechService](https://developer.android.com/reference/android/speech/tts/TextToSpeechService), [SynthesisCallback](https://developer.android.com/reference/android/speech/tts/SynthesisCallback), [SynthesisRequest](https://developer.android.com/reference/android/speech/tts/SynthesisRequest).
