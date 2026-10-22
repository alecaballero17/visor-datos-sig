(() => {
  const shell=document.querySelector('.login-shell');
  const api=shell.dataset.api;
  const form=document.getElementById('loginForm');
  const error=document.getElementById('loginError');

  async function clearNonAdminSession(session){
    if(session?.roles?.includes('Administrador')){
      location.href='/Home/Index';
      return true;
    }
    if(session) await fetch(`${api}/api/autenticacion/cerrar`,{method:'POST',credentials:'include'}).catch(()=>{});
    if(session){
      error.textContent='Esta cuenta no tiene acceso a la versión web. Solo puede ingresar el administrador.';
      error.classList.remove('d-none');
    }
    return false;
  }

  fetch(`${api}/api/autenticacion/sesion`,{credentials:'include'})
    .then(async response=>response.ok?response.json():null)
    .then(clearNonAdminSession)
    .catch(()=>{});

  form.addEventListener('submit',async event=>{
    event.preventDefault();
    error.classList.add('d-none');
    const usuario=document.getElementById('usuario').value.trim();
    const password=document.getElementById('password').value;
    if(!usuario||!password){error.textContent='Complete usuario y contraseña.';error.classList.remove('d-none');return;}
    try{
      const response=await fetch(`${api}/api/autenticacion/iniciar`,{
        method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',
        body:JSON.stringify({usuario,password})
      });
      const session=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(session.mensaje||'No fue posible iniciar sesión.');
      if(!session.roles?.includes('Administrador')){
        await fetch(`${api}/api/autenticacion/cerrar`,{method:'POST',credentials:'include'}).catch(()=>{});
        throw new Error('Esta cuenta no tiene acceso a la versión web. Solo puede ingresar el administrador.');
      }
      location.href='/Home/Index';
    }catch(exception){
      error.textContent=exception.message||'No fue posible iniciar sesión.';
      error.classList.remove('d-none');
    }
  });
})();
