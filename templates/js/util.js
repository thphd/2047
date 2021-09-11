var print = console.log
var prerr = console.error

var gebcn = e=> cn=>e.getElementsByClassName(cn)
var gebtn = e=> n=>e.getElementsByTagName(n)
var geid = i=>document.getElementById(i)
var print = console.log
var foreach = a=> f=>{
  var r = [];
  var i = 0;
  var items = [];
  for(i=0;i<a.length;i++){items.push(a[i])}
  for(i=0;i<items.length;i++){r.push(f(items[i]))}
  return r
}

function dce(t){return document.createElement(t)}

var cap = i=>Math.min(Math.max(i,0), 1)

// conversion between utf8 and arraybuffer

// https://gist.github.com/pascaldekloe/62546103a1576803dade9269ccf76330

// This is free and unencumbered software released into the public domain.

// Marshals a string to an Uint8Array.
function encodeUTF8(s) {
  var i = 0, bytes = new Uint8Array(s.length * 4);
  for (var ci = 0; ci != s.length; ci++) {
    var c = s.charCodeAt(ci);
    if (c < 128) {
      bytes[i++] = c;
      continue;
    }
    if (c < 2048) {
      bytes[i++] = c >> 6 | 192;
    } else {
      if (c > 0xd7ff && c < 0xdc00) {
        if (++ci >= s.length)
        throw new Error('UTF-8 encode: incomplete surrogate pair');
        var c2 = s.charCodeAt(ci);
        if (c2 < 0xdc00 || c2 > 0xdfff)
        throw new Error('UTF-8 encode: second surrogate character 0x' + c2.toString(16) + ' at index ' + ci + ' out of range');
        c = 0x10000 + ((c & 0x03ff) << 10) + (c2 & 0x03ff);
        bytes[i++] = c >> 18 | 240;
        bytes[i++] = c >> 12 & 63 | 128;
      } else bytes[i++] = c >> 12 | 224;
      bytes[i++] = c >> 6 & 63 | 128;
    }
    bytes[i++] = c & 63 | 128;
  }
  return bytes.subarray(0, i);
}

// Unmarshals a string from an Uint8Array.
function decodeUTF8(bytes) {
  var i = 0, s = '';
  while (i < bytes.length) {
    var c = bytes[i++];
    if (c > 127) {
      if (c > 191 && c < 224) {
        if (i >= bytes.length)
        throw new Error('UTF-8 decode: incomplete 2-byte sequence');
        c = (c & 31) << 6 | bytes[i++] & 63;
      } else if (c > 223 && c < 240) {
        if (i + 1 >= bytes.length)
        throw new Error('UTF-8 decode: incomplete 3-byte sequence');
        c = (c & 15) << 12 | (bytes[i++] & 63) << 6 | bytes[i++] & 63;
      } else if (c > 239 && c < 248) {
        if (i + 2 >= bytes.length)
        throw new Error('UTF-8 decode: incomplete 4-byte sequence');
        c = (c & 7) << 18 | (bytes[i++] & 63) << 12 | (bytes[i++] & 63) << 6 | bytes[i++] & 63;
      } else throw new Error('UTF-8 decode: unknown multibyte start 0x' + c.toString(16) + ' at index ' + (i - 1));
    }
    if (c <= 0xffff) s += String.fromCharCode(c);
    else if (c <= 0x10ffff) {
      c -= 0x10000;
      s += String.fromCharCode(c >> 10 | 0xd800)
      s += String.fromCharCode(c & 0x3FF | 0xdc00)
    } else throw new Error('UTF-8 decode: code point 0x' + c.toString(16) + ' exceeds UTF-16 reach');
  }
  return s;
}

function tryjson(s){
  try{
    j = JSON.parse(s)
    // print('parsed')
    return j
  }catch(e){
    // print('not parsed')
    return s
  }
}

// how to http
function xhr(method, dest, data){
  return new Promise((res,rej)=>{
    var r = new XMLHttpRequest();
    r.addEventListener('loadend', function(){
      if (this.status>=200 && this.status<300){
        res(tryjson(this.responseText))
      }else{
        resp = tryjson(this.responseText)
        if(resp.error){
          rej (this.status + ' '+this.statusText+ '\n' + resp.error)
        }else{
          if(this.status==0){
            var statusText='Connection Failed / 连接失败'
          }
          rej(this.status +' '+ (this.statusText||statusText) + '\n' + this.responseText.slice(100))
        }
      }
      // print(this)
    })
    r.open(method, dest)
    r.timeout = 15000;
    if (data){
      r.setRequestHeader('Content-type','application/json')
      r.send(data)
    }else{
      r.send()
    }
  })
}

var file_selector = geid('file_selector')
var btn_upload = geid('button_upload')

if (file_selector&&btn_upload){
  btn_upload.onclick=function(){
    upload_file('/upload')
  }
}

function upload_file(target){
  btn_upload.disabled=true
  var files = file_selector.files
  if(files.length==0){
    // alert('请先选择一个文件')
    isa_error('请先选择一个文件',3500)
    btn_upload.disabled=false
    return
  }

  var file = files[0];
  print(file)

  var xhrObj = new XMLHttpRequest();
  // xhrObj.upload.addEventListener("loadstart", loadStartFunction, false);
  // xhrObj.upload.addEventListener("progress", progressFunction, false);

  var isa = isa_waiting('正在上传到服务器...')
  xhrObj.upload.addEventListener("load", function(){
    // display_notice('')
    isa.set_text('完成')
    isa.delay_destruct(500)
    window.location.reload()
  }, false);
  // display_notice('正在上传到服务器...')
  xhrObj.open("POST", target, true);
  xhrObj.setRequestHeader("Content-type", file.type);
  // xhrObj.setRequestHeader("X_FILE_NAME", file.name);
  xhrObj.send(file);
}



// access api
function api(j, display){
  if(!display){
    // display_notice('连接服务器...')
    var isa = isa_waiting('连接服务器...')
  }
  var p = xhr('post', '/api', JSON.stringify(j))
  return p.then(r=>{
    if(!display){
      isa.set_text('成功')
      isa.delay_destruct(500)
    }
    return r
  })
  .catch(e=>{
    if(!display){
      isa.set_text('失败')
      isa.delay_destruct(500)
    }
    throw e
  })
}

function alert_via_isa(s){
  var eisa = isa_error(s.toString(),2000)
}

function aa(action, j, display){
  if(j){
    j.action = action
  }else{
    j = {action}
  }
  return api(j, display)
}

//  generate timed pings
function timed(interval){
  setTimeout(function(){
    var itvl = interval
    xhr('get', '/api?action=ping').then(js=>{
      if(js.interval){
        itvl = js.interval
        // print(itvl)
      }
    }).catch(prerr).then(()=>{
      timed(Math.min(itvl,30000))
    })
  }, interval)
}
timed(5000)

// use client side hashing
// such that servers need not know the actual password.

// this will protect agianst common passwords across various sites
// after publishing the database.
// this will not protect against impersonation after user logged onto another copy of the site with the published database.

// public key crypto should be added in the future.
function hash_user_pass(username, password){
  var fin = md5(password+username)
  var pi = h=>parseInt(h,16)
  var h2a = h=>h.split('').map(pi)
  var sum = k=>k.reduce((a,b)=>a+b)
  var times = 8964 + sum(h2a(fin)) * 2047 % 8964
  print(times)

  for(var i=0; i<times; i++){
    switch (pi(fin[31]) % 3){
      case 0:
      fin = md5(password+fin+username);break
      case 1:
      fin = md5(username+fin+password);break
      case 2:
      fin = md5(fin+password+username);break
      default:
      return 'this is NOT cryptographically secure but enough of a headache'
    }
  }
  return fin
}

// user register
var regbtn = geid('register')

if (regbtn){
  geid('username').focus()

  regbtn.onclick = function(){

    var username = geid('username').value
    var password = geid('password').value
    var password2 = geid('password2').value
    var invcode = geid('invitation').value

    if (password!=password2){
      alert('两次密码不一致')
      return false
    }

    if (password.length<6){
      alert('密码太短')
      return false
    }

    regbtn.disabled=true

    api({
      action:'register',
      username:username,
      password_hash:hash_user_pass(username, password),
      invitation_code:invcode,
    })
    .then(res=>{
      print(JSON.stringify(res))
      alert('注册成功，请登录')

      window.location.href = '/login?username='+username
    })
    .catch(err=>{
      alert(err)
      regbtn.disabled=false
    })
  }
}

// change password
var cpwbtn = geid('change_password')

if (cpwbtn){

  cpwbtn.onclick = function(){
    var username = geid('username').value
    var pwo = geid('old_password').value
    var pwn = geid('new_password').value
    var pw2 = geid('password2').value
    if (pwn!=pw2){
      alert('两次密码不一致')
      return false
    }
    if (pwn.length<6){
      alert('密码太短')
      return false
    }

    cpwbtn.disabled=true

    api({
      action:'change_password',
      old_password_hash:hash_user_pass(username, pwo),
      new_password_hash:hash_user_pass(username, pwn),
    })
    .then(res=>{
      print(JSON.stringify(res))
      alert('修改成功')
      window.location.reload()
    })
    .catch(err=>{
      alert(err)
      cpwbtn.disabled=false
    })
  }
}

var loginbtn = geid('login')
if (loginbtn){
  var pw = geid('password')
  var un = geid('username')

  var pgp_login = geid('pgp_login')

  un.focus()

  if(un.value.length>0){
    pw.focus()
  }

  function go_back_if_possible(){
    if (document.referrer.match('/register') ||
      document.referrer.match('/login')||
      document.referrer==""){
      window.location.href = '/'
    }else{
      // window.history.back()
      window.location.href = document.referrer
    }
  }

  loginbtn.onclick=function(){
    var username = geid('username').value
    var password = geid('password').value
    loginbtn.disabled=true
    api({
      action:'login',
      username:username,
      password_hash:hash_user_pass(username, password),
    })
    .then(res=>{
      print(res)
      go_back_if_possible()
    })
    .catch(err=>{
      alert(err)
      loginbtn.disabled=false
    })
  }

  pw.onkeypress=function(e){
    if (e.keyCode==13){
      loginbtn.click()
    }
  }

  un.onkeypress = function(e){
    if (e.keyCode==13){
      pw.focus()
    }
    if(pgp_login){
      un.onchange()
    }
  }

  if(pgp_login){
    var pgpm = geid('login_pgp_message')

    function update_pgp_commands(){
      if (un.value){
        var ts = (new Date()).toISOString()
        // geid('gpg_commands').value = `echo "2047login#${un.value.trim()}#${ts}" | gpg -u "${un.value.trim()}" --armor --clearsign`
        geid('gpg_commands').value =
         `echo "2047login##${b64encode(un.value.trim())}##${ts}" | gpg -u "${un.value.trim()}" --armor --clearsign`
      }else{
        geid('gpg_commands').value = '(请先在上方输入用户名)'
      }
    }
    update_pgp_commands()

    un.onchange = function(){
      Promise.resolve().then(()=>{setTimeout(update_pgp_commands, 200)})
    }

    // pgpm.onkeypress = pw.onkeypress
    pgpm.onkeypress = function(e){
      if (e.keyCode==13){pgp_login.click()}
    }

    pgp_login.onclick=function(){
      pgp_login.disabled=true
      api({
        action:'login_pgp',
        message:pgpm.value,
      })
      .then(res=>{
        go_back_if_possible()
      })
      .catch(err=>{
        alert(err)
        pgp_login.disabled=false
      })
    }

  }


}

function logout(){
  api({
    action:'logout'
  })
  .then(res=>{
    if(window.location.href.includes('/m') ||
      window.location.href.includes('/n')){
      window.location.href='/'
    }else{
      window.location.reload()
    }
  })
  .catch(alert)
}

function go_or_refresh_if_samepage(url){
  var hashless = url.split('#')[0]
  var old_hashless = window.location.href.split('#')[0]

  if(old_hashless.endsWith(hashless)){
    window.location.href = url
    window.location.reload()
  }else{
    window.location.href = url
  }
}


function register_if_exist(target_id,f){
  var target = geid(target_id)
  if(target){
    f()
  }
}

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
 }

// sinoencrypt sb1024
register_if_exist('btn_encrypt',function(){
  var btn_encrypt = geid('btn_encrypt')
  var btn_decrypt = geid('btn_decrypt')

  var plain = geid('ta_plain'), key = geid('ta_key'), ct = geid('ta_ct')
  var ed = geid('div_encrypted'), dd = geid('div_decrypted')

  btn_encrypt.onclick = function(){
    btn_encrypt.enabled = false
    div_encrypted.innerText = '正在连接服务器...'
    aa('sb1024_encrypt',{key:key.value, plain:plain.value}).then(res=>{
      div_encrypted.innerText = res.ct
    })
    .catch(alert)
    .then(()=>{
      btn_encrypt.enabled = true
    })
  }
  btn_decrypt.onclick = function(){
    btn_decrypt.enabled = false
    div_decrypted.innerText = '正在连接服务器...'
    aa('sb1024_decrypt',{key:key.value, ct:ct.value}).then(res=>{
      div_decrypted.innerText = res.plain
    })
    .catch(alert)
    .then(()=>{
      btn_decrypt.enabled = true
    })
  }
})


var editor_target = geid('editor_target')

if (editor_target){
  var bpreview = geid('editor_btnpreview')
  var bsubmit = geid('editor_btnsubmit')
  var bsubmitd = geid('editor_btnsubmitdelay')
  var preview = geid('editor_preview')
  var editor_text = geid('editor_text')
  var editor_title = geid('editor_title')
  var editor_right = geid('editor_right')

  var editor_checkbox = geid('editor_checkbox')

  var adjustments = foreach(
    'image,link,link_label,italic,bold,code,quote,strike'
    .split(','))(n=>{
    var editor_x = geid('editor_'+n)
    if (editor_x){
      editor_x.onclick = function(){
        var et = editor_text
        var ss = et.selectionStart
        var se = et.selectionEnd

        // selected text
        var st = et.value.substr(ss, se-ss)
        print(st)
        var stl = st.length
        var bst = et.value.substr(0, ss)
        var ast = et.value.substr(se)

        et.focus()

        switch (n) {
          case 'bold':
              et.setRangeText(`**${st}**`,ss,se,'preserve')
              et.setSelectionRange(ss+2, se+2)
            break;

            case 'italic':
              et.setRangeText(`*${st}*`,ss,se,'preserve')
              et.setSelectionRange(ss+1, se+1)
            break;

            case 'strike':
              et.setRangeText(`<s>${st}</s>`,ss,se,'preserve')
              et.setSelectionRange(ss+3, se+3)
            break;

            case 'code':
              var lines = st.split(`\n`)
              if (lines.length<=1){
                et.setRangeText(`\`${st}\``,ss,se,'preserve')
                et.setSelectionRange(ss+1, se+1)
              }else{
                var out = `\n\`\`\`text\n${st}\n\`\`\`\n`
                et.setRangeText(out,ss,se,'preserve')
                et.setSelectionRange(ss+9, ss+9+st.length)
              }

            break;

            case 'link':
              var stt = st.trim()
              var lstt = stt.length
              et.setRangeText(`<${stt}>`,ss,se,'preserve')
              et.setSelectionRange(ss+1, ss+1+lstt)
            break;

            case 'link_label':
              if (!st.trim().length){
                et.setRangeText(`[]()`,ss,se,'preserve')
                et.setSelectionRange(ss+1, ss+1)
              }else{
                var link = ''
                et.setRangeText(`[${st.trim()}](${link})`,ss,se,'preserve')
                var lll = st.trim().length + link.length
                et.setSelectionRange(ss+1+lll+2, ss+1+lll+2)
              }
            break;

            case 'image':
              et.setRangeText(`![](${st.trim()})`,ss,se,'preserve')
              if(!st.trim().length){
                et.setSelectionRange(ss+4, ss+4)
              }else{
                et.setSelectionRange(ss+2, ss+2)
              }
            break;

            case 'quote':
              // var stt = st.trim()
              var stt = st
              var lstt = stt.length

              var lines = stt.split('\n')
              // print(lines.length)

              if(lstt.length==0){
                et.setRangeText('\n>\n', ss, se, 'preserve')
                et.setSelectionRange(ss+1, ss+1)

              }else{
                if(lines.length<=5){
                  var out = foreach(lines)(line=>`> ${line}`).join('\n')
                  out = `\n${out}\n`
                  et.setRangeText(out, ss, se, 'preserve')
                  et.setSelectionRange(ss+1, ss+out.length-1)
                }else{
                  var prefix = `\n<blockquote>\n\n`
                  var out = `${prefix}${stt}\n\n</blockquote>\n`
                  et.setRangeText(out, ss, se, 'preserve')
                  et.setSelectionRange(ss+prefix.length, ss+prefix.length+lstt)
                }
              }

            break;

          default:
        }

      }
    }
  })

  editor_right.style.display = 'none'

  bpreview.onclick = function(){
    bpreview.disabled = true

    api({
      action:'render',
      content:editor_text.value
    })
    .then(j=>{
      preview.innerHTML = j.html
      editor_right.style.display = 'initial'

      if(process_all_youtube_reference){
        process_all_youtube_reference(preview)
      }

      if(hljs){
        document.querySelectorAll('pre code').forEach(block=>{
          hljs.highlightBlock(block)
        })
      }
    })
    .catch(alert)
    .then(()=>{
      bpreview.disabled = false
    })
  }

  bsubmit.onclick = function(){
    bsubmit.disabled = true
    bpreview.disabled = true

    // _type = editor_target.getAttribute('_type')
    // _id = editor_target.getAttribute('_id')
    _target = editor_target.getAttribute('_target')

    api({
      action:'post',
      target:_target,
      content:editor_text.value,
      title:editor_title?editor_title.value:null,
      mode:editor_checkbox?(editor_checkbox.checked?'question':null):null,
    })
    .then(j=>{
      // window.location.reload()
      print(j)
      // alert(j)
      editor_text.value = "" // firefox didn't clear the box
      // window.location.href = j.url
      go_or_refresh_if_samepage(j.url)

      // window.location.reload() // in case the previous doesn't work

    })
    .catch(alert)
    .then(()=>{
      bpreview.disabled = false
      bsubmit.disabled = false
    })
  }

  if(bsubmitd){
    bsubmitd.onclick = function(){
      var pr = prompt('打算延时多少秒发送呀？')
      if(pr){
        pr = parseInt(pr)
        if (pr<=1){
          geid('editor_btnsubmit').click()
          return
        }
        var c = 0
        var isa = isa_waiting('倒计时准备')
        setInterval(()=>{
          c+=1
          if (c>=pr){
            geid('editor_btnsubmit').click()
          }else{
            // display_notice(`倒计时 ${pr-c} 秒`)
            isa.set_text(`倒计时 ${pr-c} 秒`)
          }
        }, 1000)
      }
    }

  }
}

function generate_invitation_code(){
  api({
    action:'generate_invitation_code',
  })
  .then(()=>{
    window.location.reload()
  })
  .catch(alert)
}

function mark_delete(targ){
  if (!targ.startsWith('u')){
    if (!confirm('确定删除？')){
      return
    }
  }
  api({
    action:'mark_delete',
    target:targ,
  })
  .then(res=>{
    var note = (targ.startsWith('u')?'已取消删除':'已标记为删除')
    // alert(note+JSON.stringify(res))
    isa_info(note, 2000)
  })
  .catch(alert)
}

function update_votecount(targ){
  api({
    action:'update_votecount',
    target:targ,
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(alert_via_isa)
}

var upvote_buttons = gebcn(document)('upvote')

foreach(upvote_buttons)(e=>{
  var cl = e.classList
  var enabled = cl.contains('enabled')
  var has_vote = cl.contains('has_vote')
  var self_voted = cl.contains('self_voted')
  var innerspan = gebtn(e)('span')[0]

  var target = e.getAttribute('target')

  if(!target){
    return
  }

  // print(innerspan)

  var clickable = true

  e.onclick = function(){
    if(!clickable){
      return
    }

    if(!enabled){
      return
    }

    clickable = false

    function reset_things(){
      clickable = true
    }

    if(!self_voted){
      api({
        action:'cast_vote',
        target:target.trim(),
        vote:1,
      })
      .then(res=>{
        var ih = parseInt(innerspan.innerHTML)||0
        innerspan.innerHTML = (ih+1).toString()

        if(!has_vote){
          cl.add('has_vote')
          has_vote = true
        }
        cl.add('self_voted')
        self_voted = true
      })
      .catch(alert_via_isa)
      .then(reset_things)
    }else{
      api({
        action:'cast_vote',
        target:target.trim(),
        vote:0,
      })
      .then(res=>{
        var ih = parseInt(innerspan.innerHTML)||0
        innerspan.innerHTML = (ih-1).toString()

        if(ih==1){
          has_vote=false
          cl.remove('has_vote')
        }
        cl.remove('self_voted')
        self_voted = false
      })
      .catch(alert_via_isa)
      .then(reset_things)
    }
  }
})

function display_notice(str){
  var ol = geid('overlay')
  if(str){
    var ot = geid('overlay_text')
    if(!ot){return}
    geid('overlay_text_body').innerText = str
    ol.classList.add('display_enable')
    ol.style.opacity=1.
  }else{
    ol.classList.remove('display_enable')
    ol.style.opacity=0.
  }
}

function send_new_message(){
  var un = prompt('请输入对方的用户名')
  if(!un){
    return
  }
  un = un.trim()
  if(!un){
    return
  }
  window.location.href = '/editor?target=username/'+un
}

var bupi = geid('button_update_personal_info')
if(bupi){
  bupi.onclick = function(){
    var calldict = {
      action:'update_personal_info',
    }

    var dupi = geid('update_personal_info')
    var inputs = gebtn(dupi)('input')

    foreach(inputs)(e=>{
      calldict[e.id] = e.value
    })

    bupi.disabled=true
    api(calldict)
    .then(r=>{
      bupi.disabled=false
      return r
    })
    .catch(e=>{
      bupi.disabled=false
      throw e
    })
    .then(r=>{
      window.location.reload()
    })
    .catch(alert)
  }
}

function at_reply(k,un){
  var text = geid('editor_text')
  if (!text){
    return
  }

  var tli = geid(k)
  if (!un){
    var uns = gebcn(tli)('user_name')
    if(uns.length<1){
      return
    }
    uns = uns[0]
    var uname = uns.firstChild &&
      (uns.firstChild.wholeText||uns.firstChild.textContent)
      || uns.innerText
    print('uname obtained via old method')
  }else{
    var uname = un
  }

  var editor_text = text
  var et = editor_text
  var ss = et.selectionStart
  var se = et.selectionEnd

  // selected text
  var st = et.value.substr(ss, se-ss)
  // print(st)
  var stl = st.length
  var bst = et.value.substr(0, ss)
  var ast = et.value.substr(se)

  et.focus()

  var replacement = ` @${uname} <#${k}> `

  et.setRangeText(replacement, ss, se, 'preserve')
  et.setSelectionRange(ss+replacement.length, ss+replacement.length)

  // text.value += `${text.value?' ':''}@${uname} <#${k}> `
  // text.focus()
}

// post colorify
(function(){
  var rgbify = a=>`rgb(${a.join(',')})`

  function colormap(i){ // i within -1..1
      var red = [255,200,162,.65] // reddish
      var green = [235, 255, 229, 0.65] // greenish
      var c = i>=0?green:red
      i = (i>=0?i:-i)
      c[3] *= cap(i)
      return rgbify(c)
  }

  function colormap2(i){ // different shades of yellow
      var yellow = [255,255,100, 0.5]
      yellow[3]*=i
      return rgbify(yellow)
  }

  function colormap3(i){
    var c = [235, 255, 229, 0.65]
    c[3]*=i
    return c[3]?rgbify(c):''
  }


  // function vote2col(v){
  //     if(v>0){
  //         v = Math.log10(v+1)
  //     }else if (v<0) {
  //         v = -Math.log10(-v+1)
  //     }else{
  //         v = 0
  //     }
  //     // v *= 0.6
  //     v*=0.1
  //     v = Math.max(v,-1)
  //     v = Math.min(v, 1)
  //     return colormap(v)
  // }
  function vote2col(v){
    var k = cap((v-2)/20)
    print('vote', v, k)
    return colormap3(k)
  }


  var tlis = gebcn(document)('threadlistitem')
  if(tlis.length==0){return}
  foreach(tlis)(e=>{
    var voten = gebcn(e)('votenumber')
    if(voten.length==0){return}

    foreach(voten)(e1=>{
      if(e1.className.trim()=='votenumber'){
        var vote = parseInt(e1.innerText.trim()||0)
        // print(vote)
        if(vote){
          var col = vote2col(vote)
          if(col) e.style.backgroundColor = col
        }
      }
    })
  })
})()

var last_hightlight = false
function highlight_hash(){
  var hash = location.hash
  if(hash[0]=='#'){
    if(last_hightlight){
      last_hightlight.classList.remove('chosen')
    }

    var _id = hash.substr(1)
    var elem = geid(_id)
    if(elem){
      print('highlighted:',elem)
      elem.classList.add('chosen')
      elem.style='' // remove color artifacts

      last_hightlight=elem
    }
  }
}
highlight_hash()

function ban_user(uid){
  if (!confirm('确定要封禁用户 '+uid.toString()+' 吗？')){
    return
  }
  var reason = prompt('请输入封禁理由：')
  if(!reason || reason.trim().length<4){
    alert('未填写理由或理由字数不足')
    return
  }

  api({
    action:'ban_user',
    uid:uid,
    reason:reason.trim(),
  })
  .then(r=>{
    window.location.reload()
  })
  .catch(alert)
}

function ban_user_reverse(uid){
  if (!confirm('确定要解封用户 '+uid.toString()+' 吗？')){
    return
  }
  var reason = prompt('请输入解封理由：')
  if(!reason || reason.trim().length<4){
    alert('未填写理由或理由字数不足')
    return
  }

  api({
    action:'ban_user',
    uid:uid,
    reason:reason.trim(),
    reverse:'yes',
  })
  .then(r=>{
    window.location.reload()
  })
  .catch(alert)
}

function add_alias(curr_name){
  var linkedname = prompt('请输入关联账户名')
  if (linkedname){
    linkedname = linkedname.trim()
    api({
      action:'add_alias',
      name:linkedname,
      is:curr_name,
    })
    .then(res=>{
      alert('已关联至'+ curr_name)
      window.location.reload()
    })
    .catch(alert)
  }else{
    alert('未输入用户名')
  }
}

var categories = false
function move_to_category(targ){
  function ask_for_category_then_move(){
    var cat_display_str = categories.map(c=>{
      var base = `${c.cid}-${c.name}`
      while(base.length<10){base+=' '}
      return base
    })
    var buf = `请输入分类数字编号\n`
    for(var i = 0; i<categories.length; i++){
      buf+=cat_display_str[i]
      if (i%3==1){
        buf+='\n'
      }
    }

    var cid = prompt(buf)
    if(!cid){
      return
    }
    cid = parseInt(cid)
    api({
      action:'move_thread',
      target:targ,
      cid:cid,
    })
    .then(res=>{
      // do nothing
      // display_notice(`${targ} 已移动至 ${cid}`)
      // setTimeout(()=>{
      //   display_notice('')
      // },2000)

      var isa = isa_info(`${targ} 已移动至 ${cid}`, 2000)
    })
    .catch(alert)
  }

  if (!categories){
    api({
      action:'get_categories_info',
    })
    .catch(alert)
    .then(res=>{
      // print(res['categories'])
      categories = res['categories']
      ask_for_category_then_move()
    })
    .catch(alert)
  }else{
    ask_for_category_then_move()
  }
}

/* Light YouTube Embeds by @labnol */
/* Web: http://labnol.org/?p=27941 */
// modified by thphd

function process_all_youtube_reference(element2){
  function labnolThumb(id) {
      var thumb = '<img src="https://i.ytimg.com/vi/ID/hqdefault.jpg">',
          play = '<div class="play"></div>';
      return thumb.replace("ID", id) + play;
  }

  var element = element2.getElementsByClassName?element2:document
  // print('element is', element)
  var divs = gebcn(element)('youtube-player-unprocessed')

  foreach(divs)(e=>{
    print(e)

    var did = e.dataset.id
    var dts = e.dataset.ts

    var div = document.createElement('div')
    div.setAttribute("data-id", did);
    div.setAttribute("data-ts", dts);
    div.innerHTML = labnolThumb(did);

    var timestamp_attr = dts?dts.replace('?t=', '&start='):''

    div.onclick = ()=>{

      var iframet = `<iframe src="https://www.youtube.com/embed/${did}?autoplay=1${timestamp_attr}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`

      var template = document.createElement('template')
      template.innerHTML = iframet
      var iframe = template.content.firstChild

      div.parentNode.replaceChild(iframe, div);
    }

    e.className='youtube-player'
    e.appendChild(div)
  })

  var votes = gebcn(element)('poll-instance-unprocessed')

  foreach(votes)(e=>{
    print(e)

    var did = e.dataset.id
    e.className = 'poll-instance'

    api({
      action:'render_poll',
      pollid:did,
    }, true)
    .then(res=>{
      e.innerHTML = res.html
    })
    .catch(print)

  })

  var commsecs = gebcn(element)('comment_section_unprocessed')
  foreach(commsecs)(e=>{
    print(e)

    var did = e.dataset.id
    e.className = 'comment_section'

    api({
      action:'render_comments',
      parent:did,
    })
    .then(res=>{
      e.innerHTML = res.html
    })
    .catch(print)

  })

  var twsecs = gebcn(element)('twitter-tweet')
  twsecs = foreach(twsecs)(e=>e).filter(e=>e.tagName=="BLOCKQUOTE")

  if (twsecs.length){
    // https://developer.twitter.com/en/docs/twitter-for-websites/javascript-api/guides/set-up-twitter-for-websites
    window.twttr = (function(d, s, id) {
      var js, fjs = d.getElementsByTagName(s)[0],
        t = window.twttr || {};
      if (d.getElementById(id)) return t;
      js = d.createElement(s);
      js.id = id;
      js.src = "https://platform.twitter.com/widgets.js";
      fjs.parentNode.insertBefore(js, fjs);

      t._e = [];
      t.ready = function(f) {
        t._e.push(f);
      };

      return t;
    }(document, "script", "twitter-wjs"));

    // may not load immediately
    if(window.twttr.widgets&&window.twttr.widgets.load){
      window.twttr.widgets.load(element)
    }

  }

}

// https://stackoverflow.com/a/35385518
/**
 * @param {String} HTML representing a single element
 * @return {Element}
 */
function htmlToElement(html) {
    var template = document.createElement('template');
    html = html.trim(); // Never return a text node of whitespace as the result
    template.innerHTML = html;
    return template.content.firstChild;
}


function browser_check(){
  var bc = geid('browser_check').innerText
  if (!bc){
    api({
      action:'browser_check'
    }, true)
    .then(print)
    .catch(console.error)
  }else{
    print('browser, skip check')
  }
}

function viewed(){
  setTimeout(function(){
    var target = geid('viewed_target')
    if (target && target.innerText){
      if (user_browser_active){
        api({
          action:'viewed_target',
          target:target.innerText,
        }, true)
        .then(print)
        .catch(console.error)
      }else{
        // print('no user interaction, wait some more...')
        viewed()
      }
    }else{
      print('viewed not found', target)
    }
  },4*1000)
}

function viewed_v2(){
  setTimeout(function(){
    var target = geid('viewed_target_v2')
    if (target && target.innerText){
      if (user_browser_active) {
        api({
          action:'viewed_target_v2',
          target:target.innerText,
        }, true)
        .then(print)
        .catch(console.error)
      }else{
        viewed_v2()
      }
    }else{
      print('viewed v2 not found', target)
    }
  },4*1000)
}

function ondomload(f){
  document.addEventListener("DOMContentLoaded", f)
}

ondomload(process_all_youtube_reference);
ondomload(browser_check);
ondomload(viewed);
ondomload(viewed_v2);

// fold/expand
ondomload(()=>{
  var tlis = gebcn(document)('threadlistitem')

  foreach(tlis)(e=>{
    var foldable = gebcn(e)('foldable')
    if(foldable.length){foldable=foldable[0]}else{return}
    var unfold = gebcn(e)('unfold')
    if(unfold.length){unfold=unfold[0]}else{return}

    var expanded = false
    unfold.onclick = function(){
      expanded = true
      unfold.classList.add('hidden')
      foldable.classList.remove('foldable')
    }

    // change visibility of the unfold button base on necessity
    function changestateaccordingly(){
      if(((foldable.clientHeight || foldable.offsetHeight)
        < (foldable.scrollHeight-40) )&& expanded==false){
          unfold.classList.remove('hidden')
          foldable.classList.add('foldable')
      }else{
        unfold.classList.add('hidden')
        foldable.classList.remove('foldable')
      }
      // print(e.id, foldable.scrollHeight)
    }

    //because image changes the height of its container after load
    var imgs = gebtn(foldable)('img')
    foreach(imgs)(e=>{
      e.onload = ()=>{
        changestateaccordingly()
        setTimeout(changestateaccordingly, 100)
      }
    })
    // foldable.onresize = changestateaccordingly
    changestateaccordingly()
  })
})

function qr_current(){
  qr(window.location.href)
}
function qr(s){
  window.open('/qr/'+s, '_blank')
}

function setuid(uid){
  api({
    action:'become',
    uid:uid,
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(console.error)
}

var submit_exam = geid('btn_submit_exam')
if(submit_exam){
  submit_exam.onclick = function(){
    var examid = parseInt(geid('examid').content)
    print(examid)

    var radios = gebtn(document)('input')
    radios = foreach(radios)(e=>e.type=='radio'?e:null).filter(e=>e)
    // print(radios)

    var nquestions = gebcn(document)('choices').length

    var answers = []
    while (nquestions--){answers.push(-1)}

    foreach(radios)(e=>{
      if (e.checked){
        answers[parseInt(e.name)]=parseInt(e.value)
      }
    })

    print(answers)

    submit_exam.disabled=true
    api({
      action:'submit_exam',
      answers:answers,
      examid:examid,
    })
    .then(res=>{
      alert('恭喜你通过考试。你的邀请码是：'+res.code)
      window.location.href = res.url
    })
    .catch(err=>{
      alert(err)
      alert('考试未通过，请稍后重试。')
    })
  }

}

function add_question(){
  // var qs = prompt('请输入题目（格式请参考其他人的题目格式）')
  var qs = geid('add_question_text').value
  if(qs){
    api({
      action:'add_question',
      question:qs,
    })
    .then(res=>{
      window.location.reload()
    })
    .catch(alert)
  }else{
    alert('请输入题目内容')
  }
}
function add_poll(){
  // var qs = prompt('请输入题目（格式请参考其他人的题目格式）')
  var qs = geid('add_question_text').value
  if(qs){
    api({
      action:'add_poll',
      question:qs,
    })
    .then(res=>{
      window.location.reload()
    })
    .catch(alert)
  }else{
    alert('请输入投票内容')
  }
}

function add_poll_vote(id, choice, del){
  api({
    action:'add_poll_vote', pollid:id, choice:choice,
    delete:del?true:false,
  })
  .then(res=>{
    // window.location.reload()
    var polls = gebcn(document)('poll-instance')
    var p = 0
    foreach(polls)(e=>{
      var did = e.dataset.id
      if (did==id){
        // e.innerHTML = ''
        e.className = 'poll-instance-unprocessed'

        // process_all_youtube_reference(e.parentNode)
        p = Promise.resolve()
        .then(res=>process_all_youtube_reference(e.parentNode))
      }
    })
    return p
  })
  .catch(alert)
}

function modify_question(k){
  var qv = geid(k).value
  print(qv)
  api({
    action:'modify_question',
    question:qv,
    qid:k,
  })
  .then(res=>{
    // window.location.reload()

  })
  .catch(alert)
}
function modify_poll(k){
  var qv = geid(k).value
  print(qv)
  api({
    action:'modify_poll',
    question:qv,
    qid:k,
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function change_time(tid, timestamp){
  api({action:'change_time', t_manual:timestamp,tid:tid})
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function add_entity(){
  var ent_type = geid('ent_type').value
  var ent_json = geid('ent_json').value
  Promise.resolve()
  .then(()=>{
    return RJSON.parse(ent_json)
  })
  .then(parsed=>{
    return api({
      action:'add_entity',
      type:ent_type,
      doc:parsed,
    })
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function add_entity_as_text(){
  var ent_type = geid('ent_type').value
  var ent_json = geid('ent_json').value
  Promise.resolve()
  .then(()=>{
    // return RJSON.parse(ent_json)
    return ent_json.trim()
  })
  .then(parsed=>{
    return api({
      action:'add_entity',
      type:ent_type,
      doc:parsed,
    })
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function modify_entity(key){
  var ent_json = geid(key).value
  Promise.resolve()
  .then(()=>{
    return RJSON.parse(ent_json)
  })
  .then(parsed=>{
    return api({
      action:'modify_entity',
      doc:parsed,
      _key:key,
    })
  })
  .then(res=>{
    // alert('修改成功')
    isa_info('修改成功', 2000)
    // window.location.reload()
  })
  .catch(alert)
}

function delete_entity(key){
  if (!confirm('are you sure?')){
    return
  }
  api({action:'delete_entity', _key:key})
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function follow(uid, is_follow){
  aa('follow',{
    uid:uid,
    follow:is_follow,
  })
  .then(r=>{window.location.reload()})
  .catch(alert)
}

function add_to_blacklist_by_name(name, del){
  return aa('blacklist',{
    username:name,
    'delete':del,
  })
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function add_to_blacklist(del){
  var un = (prompt('请输入对方的用户名')||'').trim()
  if (un){
    return add_to_blacklist_by_name(un,del)
  }
}

// function goto(s){
//   var p = geid(s)
//   if (p){
//     window.location.href = '#'+s
//     highlight_hash()
//   }else{
//     window.location.href = '/p/'+s
//   }
// }

// #1234 links now jumps to ids within page if possible
foreach(gebtn(document)('a'))(e=>{
  if(e && e.href && e.innerHTML.startsWith('#')){
    var href = e.getAttribute('href')
    // print(href)
    var match = href.match(/^\/p\/([0-9a-z]{1,})$/)
    if(match){
      var pid = match[1]
      if(geid(pid)){
        e.href = '#'+pid
        e.onclick = function(){setTimeout(highlight_hash, 50)}
      }
    }
  }
})

function b64encode(s){
  s = encodeUTF8(s)
  s = foreach(s)(i=>{return String.fromCharCode(i)})
  s = s.reduce((a,b)=>a+b)
  return btoa(s)
}

var btn_search = geid('btn_search')
if(btn_search){
  var st = geid('search_term')
  btn_search.onclick = ()=>{
    var term = st.value.trim()

    if(!term){
      return
    }

    window.location.href = '?q='+term
  }

  st.onkeypress=function(e){
    if (e.keyCode==13){
      btn_search.click()
    }
  }
  st.focus()
}

var btn_searchpm = geid('btn_searchpm')
if(btn_searchpm){
  var st = geid('search_term')
  btn_searchpm.onclick = ()=>{
    var term = st.value.trim()

    if(!term){
      return
    }

    if(window.location.href.includes('/guizhou')){
      window.location.href = '/guizhou?q='+term
      return
    }
    window.location.href = '/ccpfinder?q='+term
  }

  st.onkeypress=function(e){
    if (e.keyCode==13){
      btn_searchpm.click()
    }
  }
  st.focus()
}

function add_tag(tid){
  var tagname = prompt('请输入标签')
  tagname = tagname.trim()
  if (!tagname){return}
  aa('edit_tag',{target:'thread/'+tid.toString(), name:tagname})
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}
function delete_tag(tid, tagname){
  if(!confirm('确定要删除标签：'+tagname+' 吗？')){return}
  aa('edit_tag',{target:'thread/'+tid.toString(), name:tagname, delete:true})
  .then(res=>{
    window.location.reload()
  })
  .catch(alert)
}

function favorite(targ, del){
  aa('favorite', {target:targ, delete:(del?true:null)})
  .then(res=>{
    var isa = isa_info(targ+(del?'已取消收藏':'已收藏'), 2000)
    // display_notice(targ+(del?'已取消收藏':'已收藏'))

    if(del){}else{
      foreach(gebcn(document)('favorite'))(e=>{
        if(e.href.includes(targ) && e.innerText.includes('收藏')){
          e.innerText = '已收藏'
          e.href = 'javascript:favorite("'+targ+'", true)'
        }
      })
    }

    // setTimeout(()=>{
    //   display_notice('')
    // }, 2000)
  })
  .catch(alert)
}

var user_browser_active = false;

(function activityWatcher(){
  var activity_counter = 0

  //An array of DOM events that should be interpreted as
  //user activity.
  var activityEvents = [
    'mousedown', 'mousemove', 'keydown',
    'scroll',
    'touchstart',
  ];

  //add these events to the document.
  //register the activity function as the listener parameter.
  activityEvents.forEach(function(eventName) {
    //The function that will be called whenever a user is active
    function activity(){
      activity_counter++;
      if(activity_counter>1){
        user_browser_active = true
        document.removeEventListener(eventName, activity)
      }
      print(eventName, activity_counter)
    }
    document.addEventListener(eventName, activity, {
      passive:true,
    });
  });
})();

function update_translation(sample, locale, original){
  var curr_lang = locale || get_meta('locale')
  var d = JSON.parse(get_meta('dict_of_languages'))
  var al = d
  var ll = ''
  for(k in al){
    ll+=`${k.toString()} ${al[k].toString()}\n`
  }

  original = original || sample
  var promptext = '请输入 <语言代码>[空格]<翻译内容>，如：\nzh-tw 登錄\n\n'+ll
  var hint = curr_lang+' '+sample

  var lang_trans = prompt(promptext, hint)

  if(!lang_trans)return

  var lang = lang_trans.split(' ')[0]
  var string = lang_trans.slice(lang.length+1)

  if (!(lang in al) || string.length<1){
    alert('所指定的语言不在支持列表内/未填写翻译内容')
    return
  }

  print(lang, string)

  aa('update_translation',{original, lang, string})
  .then(r=>{
    isa_info('提交成功。如果要查看刚刚提交的内容，请刷新页面。', 3500)
    // alert('提交成功。如果要查看刚刚提交的内容，请刷新页面。')
  })
  .catch(alert)
}

function approve_translation(id, del){
  aa('approve_translation',{id, delete:del})
  .then(r=>{
    var isa = isa_info(
      del?'已取消审核标记。':'已标记为通过审核。'+'如果要查看修改后的状态，请刷新页面。'
    ,3500)

    // setTimeout(()=>display_notice(''), 3500)
  })
  .catch(alert)
}

function get_meta(name){
  return document.querySelector(`meta[name="${name}"]`).content
}

function set_locale(l){
  aa('set_locale',{locale:l})
  .then(res=>{
    window.location.reload()
  }).catch(alert)
}

function change_name(uid, name){
  aa('change_name',{uid, name})
  .then(alert)
  .catch(alert)
}

function runcode(challenge_name, is_submission){
  code = ace_editor.getValue()
  input = geid('runcode_input').value

  print(challenge_name, code, input)
  var rcrs = geid('runcode_result')

  aa('runcode',{
    code,
    input,
    challenge_name,
    is_submission,
  })
  .then(res=>{
    rcrs.innerHTML = res.result

    if (res.error){
      rcrs.style="color:red"
      isa_error('代码运行结果可能包含错误',3500)
    }else{
      rcrs.style="color:green"
      isa_info('代码运行成功', 2000)
    }

    rcrs.scrollTop = rcrs.scrollHeight;

    if (is_submission){
      if(!res.error){
        alert('提交通过！')
        go_or_refresh_if_samepage('/leet')
      }else{
        alert('提交未通过，请检查代码。')
      }
    }
  })
  .catch(alert)
}

var isa_list = geid('overlay_notif_list')
var isa_template = gebcn(isa_list)('overlay_notif_box')[0]
isa_list.removeChild(isa_template)

function create_isa(){
  var isa = isa_template.cloneNode(true) // deep
  isa_list.appendChild(isa)
  isa.style.opacity = 1

  var textnode = gebcn(isa)('overlay_notif_text')[0]
  var bouncy = gebcn(isa)('overlay_notif_icon_inner')[0]

  function change_text(t){
    textnode.innerHTML = escapeHtml(t)
  }

  var bounce_ticker=-999;
  isa.start_bouncing = ()=>{
    var t = 0
    bounce_ticker = setInterval(()=>{
      if (t>= 2*Math.pi){
        t-=2*Math.pi
      }
      bouncy.style.opacity = Math.pow((Math.cos(t)+1)*.5, 2)
      t=t+0.2
      // bouncy.style.left = (Math.cos(t)*3).toString()+'px'
    }, 50)
  }
  isa.stop_bouncing = ()=>{
    if (bounce_ticker!=-999) clearInterval(bounce_ticker)
  }
  isa.set_color = (c)=>{
    bouncy.style.backgroundColor = c
    textnode.style.color = c
  }

  isa.destruct = ()=>{
    isa.stop_bouncing()
    var counter = 10
    var ticker = setInterval(()=>{
      isa.style.opacity = counter/10
      if (counter<=0){
        clearInterval(ticker)
        isa.parentNode.removeChild(isa)
      }
      counter=counter-1
    }, 40)
  }
  isa.set_text = (msg)=>msg?change_text(msg):isa.destruct()

  isa.delay_destruct = t=>{
    setTimeout(()=>{
      isa.destruct()
    },t)
  }
  return isa
}

function isa_info(message, t){
  var isa = create_isa()
  isa.set_text(message)
  isa.set_color('#3b70b0')
  if (t) isa.delay_destruct(t)
  return isa
}
function isa_waiting(message, t){
  var isa = create_isa()
  isa.set_text(message)
  isa.set_color('#41b7a6')
  isa.start_bouncing()
  if (t) isa.delay_destruct(t)
  return isa
}
function isa_error(message, t){
  var isa = create_isa()
  isa.set_text(message)
  isa.set_color('#c92626')
  if (t) isa.delay_destruct(t)
  return isa
}
