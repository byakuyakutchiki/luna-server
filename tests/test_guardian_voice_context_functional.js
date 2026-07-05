/**
 * Test fonctionnel autonome du pipeline vocal Guardian.
 *
 * Objectif : prouver que la phrase
 *   "Au secours, il est devant la porte, il essaie d'entrer."
 * est capturée en entier, envoyée une seule fois au backend, et ne déclenche
 * qu'une seule chaîne SOS.
 *
 * Ce test ne nécessite ni navigateur, ni micro, ni module externe :
 * il exécute les fonctions vocales de static/guardian.html dans Node.js
 * avec des stubs minimaaux.
 */

'use strict';

// ── Stubs environnement ─────────────────────────────────────────────────────
global.window = {};
global.document = {
  getElementById: function(id) {
    return {
      classList: { add: function(){}, remove: function(){} },
      textContent: '',
      style: {},
      innerHTML: ''
    };
  }
};
global.localStorage = {
  getItem: function(k){ return k==='guardian_countdown_s' ? '5' : null; },
  setItem: function(){}
};
global.navigator = {};

// ── Stubs Guardian non vocaux ───────────────────────────────────────────────
var SID = 'test-session-42';
var fetchCalls = [];
function authFetch(url, opts) {
  fetchCalls.push({url: url, opts: opts});
  return Promise.resolve({
    status: 200,
    json: function(){
      return Promise.resolve({
        success: true,
        message: 'SOS envoyé : 1 contact par SMS, 1 appel passé',
        sms_sent_to: 1,
        dm_sent_to: 0,
        calls_placed: 1
      });
    }
  });
}
function vibrate(){}
function guardianSpeak(){}
function _voiceLog(){}
function _eemStart(){}
function _eemStartAudio(){}
function _eemStartCamera(){}
function updateRisk(){}
function showAlertOnMap(){}
function breakStreak(){}
function loadEvents(){}
function showToast(){}
function _formatAlertSummary(d){ return d.message || ''; }
function escH(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function _genIncidentId(){ return 'incident-' + (++_genIncidentId._n); }
_genIncidentId._n = 0;

// ── Fonctions vocales extraites de static/guardian.html ─────────────────────

var _vocalActive = false;
var _vocalTimer = null;
var _sosInProgress = false;
var _voiceTranscript = '';
var _voiceContext = '';
var _voiceCaptureActive = false;
var _voiceCaptureTimer = null;
var _vocalRec = null;
var _vocalRestartT = null;

function _norm(s){
  return (s||'').toLowerCase()
    .replace(/[’`]/g,"'")
    .replace(/[^a-z0-9'\s]/g,' ')
    .replace(/\s+/g,' ').trim();
}

var EMERGENCY_KW = ['au secours', 'a l aide', 'aidez moi', 'help'];
var CANCEL_KW = ['annule', 'annuler', 'tout va bien', 'faux'];

function _traceGuardian(step, payload){
  // Traçage silencieux dans ce test ; en vrai la fonction poste sur /api/debug/log
}

function _renderVoiceContext(){
  var el = document.getElementById('vocal-context');
  if(!el) return;
  if(!_voiceContext && !_voiceTranscript){ el.style.display='none'; return; }
  var parts=[];
  if(_voiceContext) parts.push('<strong>'+escH(_voiceContext)+'</strong>');
  if(_voiceTranscript) parts.push('<span style="color:var(--muted);">« '+escH(_voiceTranscript)+' »</span>');
  el.innerHTML=parts.join('<br>');
  el.style.display='block';
}

function _enrichVoiceContext(transcript){
  if(!transcript) return;
  authFetch('/api/guardian/voice-context',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({transcript:transcript})
  }).then(function(r){return r.json();}).then(function(d){
    if(d&&d.summary){ _voiceContext=d.summary; if(_vocalActive) _renderVoiceContext(); }
  }).catch(function(){});
}

function _stopVoiceCapture(){
  _voiceCaptureActive=false;
  if(_voiceCaptureTimer){ clearTimeout(_voiceCaptureTimer); _voiceCaptureTimer=null; }
}

function openVocalCountdown(){
  if(_vocalActive||_sosInProgress) return;
  _vocalActive=true;
  var n=parseInt(localStorage.getItem('guardian_countdown_s')||'15',10);
  if(!(n>=5&&n<=60)) n=15;
  _renderVoiceContext();
  vibrate([300,100,300]);

  _vocalTimer=setInterval(function(){
    n--;
    if(n<=0){
      clearInterval(_vocalTimer); _vocalTimer=null;
      if(_vocalRec){ try{_vocalRec.abort();}catch(e){} _vocalRec=null; }
      if(_vocalRestartT){ clearTimeout(_vocalRestartT); _vocalRestartT=null; }
      _vocalActive=false;
      _triggerSOSVocal();
    }
  },1000);
}

function _vocalMatch(transcript,isFinal){
  var t=(transcript||'').trim();
  var n=_norm(t);
  if(_vocalActive||_sosInProgress){
    if(_vocalActive && CANCEL_KW.some(function(k){return n.includes(_norm(k));})) cancelVocalCountdown();
    return;
  }

  if(_voiceCaptureActive){
    if(t){
      _voiceTranscript=t;
      _voiceContext=t;
      _traceGuardian('web_sr_context',{isFinal:!!isFinal, transcript:t, voiceContext:_voiceContext});
    }
    if(isFinal){
      _traceGuardian('web_sr_capture_final',{voiceTranscript:_voiceTranscript, voiceContext:_voiceContext});
      _stopVoiceCapture();
      openVocalCountdown();
    }
    return;
  }

  var _padded=' '+n+' ';
  var hit=EMERGENCY_KW.some(function(k){
    return _padded.includes(' '+_norm(k)+' ');
  });
  if(hit){
    _voiceTranscript=t;
    _voiceContext=t;
    _traceGuardian('web_sr_hit',{path:'_vocalMatch', transcript:t, keywordMatched:true, voiceTranscript:_voiceTranscript, voiceContext:_voiceContext});
    _voiceCaptureActive=true;
    _voiceCaptureTimer=setTimeout(function(){
      _traceGuardian('web_sr_capture_timeout',{voiceTranscript:_voiceTranscript, voiceContext:_voiceContext});
      _stopVoiceCapture();
      openVocalCountdown();
    },4000);
  } else {
    _traceGuardian('web_sr_no_hit',{path:'_vocalMatch', transcript:t, keywordMatched:false});
  }
}

function cancelVocalCountdown(){
  _stopVoiceCapture();
  if(!_vocalActive) return;
  clearInterval(_vocalTimer); _vocalTimer=null;
  _vocalActive=false;
  _voiceTranscript='';
  _voiceContext='';
  showToast('Annulé',3000);
  vibrate([50]);
  _voiceLog('voice_cancelled','user_cancel');
  guardianSpeak('État d\'urgence désactivé.');
}

function _triggerSOSVocal(){
  if(!SID||_sosInProgress) return;
  _sosInProgress=true;
  var iid=_genIncidentId();
  vibrate([500,150,500,150,800]);
  guardianSpeak('Contact d\'urgence activé.');
  _eemStart(iid,'vocal');
  var sosPayload={incident_id:iid,source:'vocal',context:_voiceContext||'',transcript:_voiceTranscript||''};
  _traceGuardian('sos_request',{path:'_triggerSOSVocal', payload:sosPayload});
  authFetch('/api/guardian/sos/'+SID,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(sosPayload)
  }).then(function(r){
    return r.json().then(function(d){return {status:r.status,data:d};});
  }).then(function(res){
    _traceGuardian('sos_response',{status:res.status, data:res.data});
    if(res.status===409){showToast('⏳ Alerte déjà envoyée',3000);return;}
    var d=res.data;
    var summary=_formatAlertSummary(d);
    showToast('🆘 '+(d.message||'SOS envoyé'),6000);
    _voiceLog('voice_alert_sent',(d.sms_sent_to||0)+'sms/'+(d.dm_sent_to||0)+'dm/'+(d.calls_placed||0)+'calls');
    guardianSpeak('Contact d\'urgence activé. Vos contacts ont été prévenus.');
    updateRisk(1,'critical','SOS vocal');
    showAlertOnMap('🆘 SOS vocal — ' + summary, null, null);
    breakStreak(); loadEvents();
    _eemStartAudio(iid);
    _eemStartCamera(iid);
  }).catch(function(e){
    _traceGuardian('sos_error',{error:e.message||String(e)});
    showToast('❌ SOS: '+(e.message||'erreur'));
  }).finally(function(){
    _sosInProgress=false;
    _voiceTranscript='';
    _voiceContext='';
  });
}

window.lunaEmergencyVoiceDetected=function(text, confidence, context){
  if(!SID){ return; }
  if(_sosInProgress){ return; }
  if(_vocalActive){ return; }
  _voiceTranscript=(text||'').toString();
  _voiceContext=(context||'').toString();
  openVocalCountdown();
  _enrichVoiceContext(_voiceTranscript);
};

// ── Scénario de test ────────────────────────────────────────────────────────

var PHRASE = "Au secours, il est devant la porte, il essaie d'entrer.";
var failures = [];

function assert(cond, msg){
  if(!cond) failures.push(msg);
}

function log(msg){ console.log(msg); }

async function run(){
  log('');
  log('=== Test flux vocal Guardian ===');
  log('Phrase testée : "' + PHRASE + '"');
  log('');

  // ── Scénario A : Web Speech (hit → capture contexte → countdown → SOS) ──
  log('--- Scénario A : Web Speech ---');

  // Simulation Web Speech : résultat intermédiaire avec le mot-clé
  log('1. Détection du mot-clé (interim) : "au secours"');
  _vocalMatch("au secours", false);

  assert(_voiceCaptureActive, 'La capture active devrait être démarrée après le hit');
  assert(_voiceTranscript === 'au secours', 'Le transcript devrait contenir le mot-clé initial');
  log('   _voiceCaptureActive=' + _voiceCaptureActive);
  log('   _voiceTranscript="' + _voiceTranscript + '"');

  // Simulation : la suite de la phrase arrive en résultat final
  log('');
  log('2. Arrivée de la phrase complète (final)');
  _vocalMatch(PHRASE, true);

  assert(!_voiceCaptureActive, 'La capture active devrait être arrêtée après isFinal');
  assert(_vocalActive, 'Le countdown devrait être actif');
  assert(_voiceTranscript === PHRASE, 'Le transcript devrait contenir la phrase complète');
  assert(_voiceContext === PHRASE, 'Le contexte devrait contenir la phrase complète');
  log('   _voiceTranscript="' + _voiceTranscript + '"');
  log('   _voiceContext="' + _voiceContext + '"');
  log('   _vocalActive=' + _vocalActive);

  // Attendre la fin du countdown
  log('');
  log('3. Attente de la fin du countdown (5 s)...');
  await new Promise(function(r){ setTimeout(r, 6500); });
  log('   Après attente : _vocalActive=' + _vocalActive + ' _sosInProgress=' + _sosInProgress);
  log('   fetchCalls.length=' + fetchCalls.length);

  // Vérifier qu'un seul POST SOS a été émis
  log('');
  log('4. Vérification des appels backend');
  var sosCalls = fetchCalls.filter(function(c){ return c.url.indexOf('/api/guardian/sos/') >= 0; });
  var contextCalls = fetchCalls.filter(function(c){ return c.url.indexOf('/api/guardian/voice-context') >= 0; });

  log('   Nombre de POST /api/guardian/sos/{SID} : ' + sosCalls.length);
  log('   Nombre de POST /api/guardian/voice-context : ' + contextCalls.length);
  assert(sosCalls.length === 1, 'Il doit y avoir exactement UN appel SOS');
  // Web Speech : le contexte est capturé on-device ; pas d'appel voice-context ici.
  assert(contextCalls.length === 0, 'Web Speech ne doit pas appeler voice-context (contexte local)');

  var payload = JSON.parse(sosCalls[0].opts.body);
  log('   Payload SOS :');
  log('     incident_id = ' + payload.incident_id);
  log('     source      = ' + payload.source);
  log('     context     = ' + payload.context);
  log('     transcript  = ' + payload.transcript);

  assert(payload.source === 'vocal', 'La source doit être "vocal"');
  assert(payload.context === PHRASE, 'Le contexte doit contenir la phrase complète');
  assert(payload.transcript === PHRASE, 'Le transcript doit contenir la phrase complète');

  // ── Scénario B : Vosk natif (appel direct + enrichissement serveur) ──
  log('');
  log('--- Scénario B : Vosk natif ---');
  fetchCalls.length = 0;
  _sosInProgress = false;
  _vocalActive = false;
  _voiceTranscript = '';
  _voiceContext = '';

  log('1. Appel de window.lunaEmergencyVoiceDetected avec la phrase complète');
  window.lunaEmergencyVoiceDetected(PHRASE, 0.95, PHRASE);

  assert(_vocalActive, 'Le countdown devrait être actif après Vosk');
  assert(_voiceTranscript === PHRASE, 'Le transcript Vosk devrait contenir la phrase complète');
  log('   _voiceTranscript="' + _voiceTranscript + '"');

  log('');
  log('2. Attente de la fin du countdown...');
  await new Promise(function(r){ setTimeout(r, 6500); });

  var sosCallsVosk = fetchCalls.filter(function(c){ return c.url.indexOf('/api/guardian/sos/') >= 0; });
  var contextCallsVosk = fetchCalls.filter(function(c){ return c.url.indexOf('/api/guardian/voice-context') >= 0; });
  log('   Nombre de POST /api/guardian/sos/{SID} : ' + sosCallsVosk.length);
  log('   Nombre de POST /api/guardian/voice-context : ' + contextCallsVosk.length);
  assert(sosCallsVosk.length === 1, 'Vosk doit déclencher exactement UN appel SOS');
  assert(contextCallsVosk.length === 1, 'Vosk doit appeler voice-context une fois pour enrichir le contexte');

  var payloadVosk = JSON.parse(sosCallsVosk[0].opts.body);
  assert(payloadVosk.context === PHRASE, 'Contexte Vosk = phrase complète');
  assert(payloadVosk.transcript === PHRASE, 'Transcript Vosk = phrase complète');

  // ── Scénario C : anti-doublon ──
  log('');
  log('--- Scénario C : anti-doublon ---');
  fetchCalls.length = 0;
  _sosInProgress = true; // simuler un SOS en cours
  _vocalActive = false;

  log('Tentative de redéclenchement Web Speech pendant _sosInProgress=true');
  _vocalMatch(PHRASE, true);
  log('Tentative de redéclenchement Vosk pendant _sosInProgress=true');
  window.lunaEmergencyVoiceDetected(PHRASE, 0.9, PHRASE);

  var sosCallsAfter = fetchCalls.filter(function(c){ return c.url.indexOf('/api/guardian/sos/') >= 0; });
  log('   Nombre de POST SOS après tentatives de doublon : ' + sosCallsAfter.length);
  assert(sosCallsAfter.length === 0, 'Aucun nouvel appel SOS ne doit être émis pendant _sosInProgress');

  // Résumé
  log('');
  if(failures.length === 0){
    log('✅ SUCCÈS : un seul déclenchement, phrase complète transmise, anti-doublon OK.');
    process.exit(0);
  } else {
    log('❌ ÉCHECS :');
    failures.forEach(function(f){ log('  - ' + f); });
    process.exit(1);
  }
}

run().catch(function(e){
  console.error(e);
  process.exit(1);
});
