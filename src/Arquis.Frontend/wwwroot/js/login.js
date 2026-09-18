(() => {
  const shell=document.querySelector('.login-shell'); const api=shell.dataset.api;
  const form=document.getElementById('loginForm'); const error=document.getElementById('loginError');
  fetch(`${api}/api/autenticacion/sesion`,{credentials:'include'}).then(r=>{if(r.ok) location.href='/Home/Index';}).catch(()=>{});
  const register=document.getElementById('registerForm'),toggle=document.getElementById('toggleRegister'),notice=document.getElementById('loginNotice');
  function registrationMode(active){form.classList.toggle('d-none',active);register.classList.toggle('d-none',!active);toggle.textContent=active?'Ya tengo cuenta':'Registrar usuario';toggle.setAttribute('aria-expanded',String(active));error.classList.add('d-none');document.getElementById('registerError').classList.add('d-none');notice.classList.add('d-none');document.getElementById(active?'registerName':'usuario').focus();}
  toggle.addEventListener('click',()=>registrationMode(register.classList.contains('d-none')));
  register.addEventListener('submit',async e=>{
    e.preventDefault();if(!register.reportValidity())return;
    const feedback=document.getElementById('registerError'),button=register.querySelector('[type="submit"]');feedback.classList.add('d-none');button.disabled=true;
    try{
      const email=document.getElementById('registerEmail').value.trim();
      const r=await fetch(`${api}/api/autenticacion/registrar`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nombre:document.getElementById('registerName').value.trim(),email,password:document.getElementById('registerPassword').value})});
      const data=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(data.mensaje||'Revise su nombre, email y contraseña e intente nuevamente.');
      register.reset();registrationMode(false);document.getElementById('usuario').value=email;notice.textContent=data.mensaje;notice.classList.remove('d-none');document.getElementById('password').focus();
    }catch(ex){feedback.textContent=ex.message;feedback.classList.remove('d-none');}finally{button.disabled=false;}
  });
  form.addEventListener('submit', async e => {
    e.preventDefault(); error.classList.add('d-none');
    const usuario=document.getElementById('usuario').value.trim(); const password=document.getElementById('password').value;
    if(!usuario || !password){error.textContent='Complete usuario y contraseña.'; error.classList.remove('d-none'); return;}
    try{
      const r=await fetch(`${api}/api/autenticacion/iniciar`,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({usuario,password})});
      if(!r.ok){const j=await r.json().catch(()=>({})); throw new Error(j.mensaje||'No fue posible iniciar sesión.');}
      location.href='/Home/Index';
    }catch(ex){error.textContent=ex.message; error.classList.remove('d-none');}
  });
})();
