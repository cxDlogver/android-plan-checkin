package com.xiang.verification.reader;

import android.media.AudioFormat;
import android.os.Bundle;
import android.speech.tts.SynthesisCallback;
import android.speech.tts.SynthesisRequest;
import android.speech.tts.TextToSpeech;
import android.speech.tts.TextToSpeechService;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** Isolated emulator tool: records the PCM actually returned for TalkBack TTS requests. */
public final class ReaderService extends TextToSpeechService {
  private static final String BACKEND="com.reecedunn.espeak",TAG="PlanCheckinSpeechEvidence";
  private final CountDownLatch ready=new CountDownLatch(1);
  private volatile CountDownLatch completion;
  private volatile String activeUtterance;
  private volatile int initialization=TextToSpeech.ERROR,finished=TextToSpeech.ERROR;
  private volatile boolean stopping;
  private TextToSpeech backend;
  private int sequence;
  @Override public void onCreate(){super.onCreate();backend=new TextToSpeech(this,status->{initialization=status;ready.countDown();},BACKEND);backend.setOnUtteranceProgressListener(new UtteranceProgressListener(){
    @Override public void onStart(String id){Log.i(TAG,"Backend started "+id);}
    @Override public void onDone(String id){if(!id.equals(activeUtterance))return;finished=TextToSpeech.SUCCESS;CountDownLatch latch=completion;if(latch!=null)latch.countDown();}
    @Override public void onError(String id){if(!id.equals(activeUtterance))return;finished=TextToSpeech.ERROR;CountDownLatch latch=completion;if(latch!=null)latch.countDown();}
    @Override public void onStop(String id,boolean interrupted){onError(id);}
  });}
  @Override public void onDestroy(){if(backend!=null)backend.shutdown();super.onDestroy();}
  @Override protected String[] onGetLanguage(){return new String[]{"zho","CHN",""};}
  @Override protected int onIsLanguageAvailable(String language,String country,String variant){return Arrays.asList("zh","zho","chi","cmn","en","eng").contains(language)?TextToSpeech.LANG_COUNTRY_AVAILABLE:TextToSpeech.LANG_NOT_SUPPORTED;}
  @Override protected int onLoadLanguage(String language,String country,String variant){return onIsLanguageAvailable(language,country,variant);}
  @Override protected void onStop(){stopping=true;if(backend!=null)backend.stop();CountDownLatch latch=completion;if(latch!=null)latch.countDown();}
  @Override protected void onSynthesizeText(SynthesisRequest request,SynthesisCallback callback){
    final long started=System.currentTimeMillis();String text=request.getCharSequenceText().toString(),id=started+"-"+(++sequence);File wav=new File(getCacheDir(),id+".wav");boolean recorded=false;int offered=0;
    try{
      if(!ready.await(15,TimeUnit.SECONDS)||initialization!=TextToSpeech.SUCCESS)throw new IllegalStateException("eSpeak initialization failed");
      stopping=false;finished=TextToSpeech.ERROR;activeUtterance=id;completion=new CountDownLatch(1);
      Locale locale=text.codePoints().anyMatch(c->Character.UnicodeScript.of(c)==Character.UnicodeScript.HAN)?Locale.SIMPLIFIED_CHINESE:Locale.US;
      int languageResult=backend.setLanguage(locale);if(languageResult<TextToSpeech.LANG_AVAILABLE)throw new IllegalStateException("Language unavailable: "+locale+" result "+languageResult);
      backend.setSpeechRate(request.getSpeechRate()/100f);backend.setPitch(request.getPitch()/100f);
      if(backend.synthesizeToFile(text,new Bundle(),wav,id)!=TextToSpeech.SUCCESS||!completion.await(30,TimeUnit.SECONDS)||finished!=TextToSpeech.SUCCESS||stopping)throw new IllegalStateException("eSpeak file synthesis stopped or failed");
      byte[] audio=Files.readAllBytes(wav.toPath());ByteBuffer b=ByteBuffer.wrap(audio).order(ByteOrder.LITTLE_ENDIAN);int sampleRate=0,channels=0,bits=0,dataStart=0,dataSize=0;
      if(audio.length<44||!new String(audio,0,4,java.nio.charset.StandardCharsets.US_ASCII).equals("RIFF"))throw new IllegalStateException("Missing WAV header");
      for(int p=12;p+8<=audio.length;){String chunk=new String(audio,p,4,java.nio.charset.StandardCharsets.US_ASCII);int size=b.getInt(p+4);if(size<0||p+8L+size>audio.length)throw new IllegalStateException("Invalid WAV chunk");if(chunk.equals("fmt ")){if(b.getShort(p+8)!=1)throw new IllegalStateException("Expected PCM");channels=b.getShort(p+10);sampleRate=b.getInt(p+12);bits=b.getShort(p+22);}if(chunk.equals("data")){dataStart=p+8;dataSize=size;break;}p+=8+size+(size&1);}
      if(dataSize<=0||sampleRate<=0||(bits!=16&&bits!=8))throw new IllegalStateException("Empty or unsupported PCM");
      if(callback.start(sampleRate,bits==16?AudioFormat.ENCODING_PCM_16BIT:AudioFormat.ENCODING_PCM_8BIT,channels)!=TextToSpeech.SUCCESS)throw new IllegalStateException("Audio callback start failed");
      for(int p=dataStart;p<dataStart+dataSize&&!stopping;){int n=Math.min(callback.getMaxBufferSize(),dataStart+dataSize-p);if(callback.audioAvailable(audio,p,n)!=TextToSpeech.SUCCESS)throw new IllegalStateException("Audio callback rejected data");offered+=n;p+=n;}
      String[] callers=getPackageManager().getPackagesForUid(request.getCallerUid());recorded=callers!=null&&Arrays.asList(callers).contains("com.android.talkback");
      if(recorded){File out=new File(getFilesDir(),id+".wav");Files.write(out.toPath(),audio);JSONObject meta=new JSONObject();meta.put("text",text).put("callerUid",request.getCallerUid()).put("callerPackages",new org.json.JSONArray(callers)).put("backend",BACKEND).put("locale",locale.toLanguageTag()).put("languageResult",languageResult).put("requestLanguage",request.getLanguage()).put("requestCountry",request.getCountry()).put("sampleRate",sampleRate).put("channels",channels).put("bits",bits).put("pcmBytes",dataSize).put("offeredBytes",offered).put("stopped",stopping).put("startedAtMs",started).put("completedAtMs",System.currentTimeMillis());Files.write(new File(getFilesDir(),id+".json").toPath(),meta.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8));Log.i(TAG,"TalkBack PCM delivered "+id+" "+offered+"/"+dataSize+" bytes");}
      if(stopping)callback.error();callback.done();
    }catch(Exception error){Log.e(TAG,"Speech request failed "+id,error);callback.error();callback.done();}
    finally{activeUtterance=null;completion=null;wav.delete();}
  }
}
