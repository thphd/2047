var print = console.log
var prerr = console.error

var gebcn = e=> cn=>e.getElementsByClassName(cn)
var gebtn = e=> n=>e.getElementsByTagName(n)
var geid = i=>document.getElementById(i)
var print = console.log
var foreach = a=> f=>{var r=[];for(var i=0;i<a.length;i++){r.push(f(a[i]))}return r}

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
            var statusText='(Connection Failed, maybe try again)'
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
    btn_upload.disabled=true
    upload_file('/upload')
  }
}

function upload_file(target){

  var files = file_selector.files
  if(files.length==0){
    alert('请先选择一个文件')
    return
  }

  var file = files[0];
  print(file)

  var xhrObj = new XMLHttpRequest();
  // xhrObj.upload.addEventListener("loadstart", loadStartFunction, false);
  // xhrObj.upload.addEventListener("progress", progressFunction, false);
  xhrObj.upload.addEventListener("load", function(){
    display_notice('')
    window.location.reload()
  }, false);
  display_notice('正在上传到服务器...')
  xhrObj.open("POST", target, true);
  xhrObj.setRequestHeader("Content-type", file.type);
  // xhrObj.setRequestHeader("X_FILE_NAME", file.name);
  xhrObj.send(file);
}



// access api
function api(j){
  display_notice('连接服务器...')
  var p = xhr('post', '/api', JSON.stringify(j))
  return p.then(r=>{
    display_notice('')
    return r
  })
  .catch(e=>{
    display_notice('')
    throw e
  })
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
      timed(itvl)
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
  geid('username').focus()
  if(geid('username').value.length>0){
    geid('password').focus()
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
      if (document.referrer.match('/register')||document.referrer==""){
        window.location.href = '/'
      }else{
        // window.history.back()
        window.location.href = document.referrer
      }
    })
    .catch(err=>{
      alert(err)
      loginbtn.disabled=false
    })
  }
}

function logout(){
  api({
    action:'logout'
  })
  .then(res=>{
    if(window.location.href.includes('/m')){
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

var editor_target = geid('editor_target')

if (editor_target){
  var bpreview = geid('editor_btnpreview')
  var bsubmit = geid('editor_btnsubmit')
  var preview = geid('editor_preview')
  var editor_text = geid('editor_text')
  var editor_title = geid('editor_title')
  var editor_right = geid('editor_right')

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
              et.setRangeText(`~~${st}~~`,ss,se,'preserve')
              et.setSelectionRange(ss+2, se+2)
            break;

            case 'code':
              et.setRangeText(`\`${st}\``,ss,se,'preserve')
              et.setSelectionRange(ss+1, se+1)
            break;

            case 'link':
              var stt = st.trim()
              var lstt = stt.length
              et.setRangeText(`<${stt}>`,ss,se,'preserve')
              et.setSelectionRange(ss+1, ss+1+lstt)
            break;

            case 'link_label':
              et.setRangeText(`[](${st.trim()})`,ss,se,'preserve')
              et.setSelectionRange(ss+1, ss+1)
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
              var stt = st.trim()
              var lstt = stt.length
              if(bst[ss-1]=='\n'){
                et.setRangeText(`> ${stt}\n`,ss,se,'preserve')
                et.setSelectionRange(ss+2, ss+2+lstt)
              }else{
                et.setRangeText(`\n> ${stt}\n`,ss,se,'preserve')
                et.setSelectionRange(ss+3, ss+3+lstt)
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
        process_all_youtube_reference()
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
      title:editor_title?editor_title.value:null
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

function highlight_hash(){
  var hash = location.hash
  if(hash[0]=='#'){
    var _id = hash.substr(1)
    var elem = geid(_id)
    if(elem){
      print(elem)
      elem.className+=' chosen'
    }
  }
}
highlight_hash()

function mark_delete(targ){
  api({
    action:'mark_delete',
    target:targ,
  })
  .then(res=>{
    var note = (targ.startsWith('u')?'已取消删除':'已标记为删除')
    alert(note+JSON.stringify(res))
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
  .catch(alert)
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
      .catch(alert)
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
      .catch(alert)
      .then(reset_things)
    }
  }
})

function display_notice(str){
  if(str){
    geid('overlay_text').innerText = str
    geid('overlay').style.display = 'block'
  }else{
    geid('overlay').style.display = 'none'
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

function at_reply(k){
  var text = geid('editor_text')
  if (!text){
    return
  }

  var tli = geid(k)
  var uns = gebcn(tli)('user_name')
  if(uns.length<1){
    return
  }
  uns = uns[0]
  var uname = uns.innerText
  var url = `/p/${k}`

  text.value += `@${uname} <#${k}> `
  text.focus()
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


  function vote2col(v){
      if(v>0){
          v = Math.log10(v+1)
      }else if (v<0) {
          v = -Math.log10(-v+1)
      }else{
          v = 0
      }
      v *= 0.6
      v = Math.max(v,-1)
      v = Math.min(v, 1)
      return colormap(v)
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
        var col = vote2col(vote)
        e.style.backgroundColor = col
      }
    })
  })
})()

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
      alert('已关联至', curr_name)
      window.location.reload()
    })
    .catch(alert)
  }else{
    alert('未输入用户名')
  }
}

/* Light YouTube Embeds by @labnol */
/* Web: http://labnol.org/?p=27941 */
// modified by thphd

function process_all_youtube_reference(){
  function labnolThumb(id) {
      var thumb = '<img src="https://i.ytimg.com/vi/ID/hqdefault.jpg">',
          play = '<div class="play"></div>';
      return thumb.replace("ID", id) + play;
  }

  var divs = gebcn(document)('youtube-player-unprocessed')

  foreach(divs)(e=>{
    var did = e.dataset.id
    var div = document.createElement('div')
    div.setAttribute("data-id", did);
    div.innerHTML = labnolThumb(did);

    div.onclick = ()=>{
      // var iframe = document.createElement("iframe");

      var iframet = `<iframe src="https://www.youtube.com/embed/${did}?autoplay=1" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`

      var template = document.createElement('template')
      template.innerHTML = iframet
      var iframe = template.content.firstChild

      // var embed = "https://www.youtube.com/embed/ID?autoplay=1";
      // iframe.setAttribute("src", embed.replace("ID", div.dataset.id));
      // iframe.setAttribute("frameborder", "0");
      // iframe.setAttribute("allowfullscreen", "1");
      div.parentNode.replaceChild(iframe, div);
    }

    e.appendChild(div)
    e.className='youtube-player'
  })
}

document.addEventListener("DOMContentLoaded", process_all_youtube_reference);
