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
    upload_file('/upload')
  }
}

function upload_file(target){
  btn_upload.disabled=true
  var files = file_selector.files
  if(files.length==0){
    alert('请先选择一个文件')
    btn_upload.disabled=false
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
function api(j, display){
  if(!display){display_notice('连接服务器...')}
  var p = xhr('post', '/api', JSON.stringify(j))
  return p.then(r=>{
    if(!display){display_notice('')}
    return r
  })
  .catch(e=>{
    if(!display){display_notice('')}
    throw e
  })
}

function aa(action, j, display){
  j.action = action
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
  var pw = geid('password')
  var un = geid('username')

  var pgp_login = geid('pgp_login')

  un.focus()

  if(un.value.length>0){
    pw.focus()
  }

  function go_back_if_possible(){
    if (document.referrer.match('/register')||document.referrer==""){
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
        setInterval(()=>{
          c+=1
          if (c>=pr){
            geid('editor_btnsubmit').click()
          }else{
            display_notice(`倒计时 ${pr-c} 秒`)
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
    var ot = geid('overlay_text')
    if(!ot){return}
    geid('overlay_text_body').innerText = str
    geid('overlay').style.opacity=1.
  }else{
    geid('overlay').style.opacity=0.
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
  var uname = uns.firstChild &&
    (uns.firstChild.wholeText||uns.firstChild.textContent)
    || uns.innerText
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
    var k = Math.max(0,(v-2)/20)
    k = Math.min(1,k)
    k = Math.pow(k,1)
    print(k)
    return colormap(k)
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
      display_notice(`${targ} 已移动至 ${cid}`)
      setTimeout(()=>{
        display_notice('')
      },2000)
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

function process_all_youtube_reference(){
  function labnolThumb(id) {
      var thumb = '<img src="https://i.ytimg.com/vi/ID/hqdefault.jpg">',
          play = '<div class="play"></div>';
      return thumb.replace("ID", id) + play;
  }

  var divs = gebcn(document)('youtube-player-unprocessed')

  foreach(divs)(e=>{
    print(e)

    var did = e.dataset.id
    var div = document.createElement('div')
    div.setAttribute("data-id", did);
    div.innerHTML = labnolThumb(did);

    div.onclick = ()=>{

      var iframet = `<iframe src="https://www.youtube.com/embed/${did}?autoplay=1" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`

      var template = document.createElement('template')
      template.innerHTML = iframet
      var iframe = template.content.firstChild

      div.parentNode.replaceChild(iframe, div);
    }

    e.className='youtube-player'
    e.appendChild(div)
  })
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
    var target = geid('viewed_target').innerText
    if (target){
      api({
        action:'viewed_target',
        target:target,
      }, true)
      .then(print)
      .catch(console.error)
    }
  },5*1000)
}

document.addEventListener("DOMContentLoaded", process_all_youtube_reference);
document.addEventListener("DOMContentLoaded", browser_check);
document.addEventListener("DOMContentLoaded", viewed);

// fold/expand
document.addEventListener("DOMContentLoaded", ()=>{
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
      e.onload = changestateaccordingly
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

function modify_question(k){
  var qv = geid(k).value
  print(qv)
  api({
    action:'modify_question',
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
    window.location.reload()
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

    window.location.href = '/search?q='+term
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
