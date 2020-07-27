var print = console.log
var prerr = console.error

function xhr(method, dest, data){
  return new Promise((res,rej)=>{
    var r = new XMLHttpRequest();
    r.addEventListener('loadend', function(){
      if (this.status>=200 && this.status<300){
        res(this.responseText)
      }else{
        rej(this.status +' '+ this.statusText)
      }
      // print(this)
    })
    r.open(method, dest)
    r.timeout = 5000;
    r.send(data)
  })
}

//  generate timed pings
function timed(interval){
  setTimeout(function(){
    var itvl = interval
    xhr('get', '../ping').then(jt=>{
      var js = JSON.parse(jt)
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
