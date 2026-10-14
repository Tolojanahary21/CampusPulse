import test, {afterEach, mock} from "node:test";
import assert from "node:assert/strict";
import {api, ApiError, csrfToken, mutate} from "../src/lib/api.ts";

afterEach(()=>{mock.restoreAll();Reflect.deleteProperty(globalThis,"document");Reflect.deleteProperty(globalThis,"window");});

test("mutations send the session and CSRF token, preserving caller headers",async()=>{
  Object.defineProperty(globalThis,"document",{value:{cookie:"other=123; campuspulse_csrf=token%3Dvalue"},configurable:true});
  const fetchMock=mock.method(globalThis,"fetch",async(_url:unknown,init?:RequestInit)=>{
    assert.equal(init?.credentials,"include");
    const headers=new Headers(init?.headers);
    assert.equal(headers.get("X-CSRF-Token"),"token=value");
    assert.equal(headers.get("Content-Type"),"application/json");
    assert.equal(headers.get("X-Request-ID"),"request-1");
    return Response.json({id:"new-post"},{status:201});
  });
  const result=await api<{id:string}>("/community/posts",{method:"POST",headers:{"X-Request-ID":"request-1"},body:JSON.stringify({content:"Bonjour"})});
  assert.equal(result.id,"new-post");assert.equal(fetchMock.mock.callCount(),1);
});

test("multipart upload lets the browser create the boundary",async()=>{
  mock.method(globalThis,"fetch",async(_url:unknown,init?:RequestInit)=>{assert.equal(new Headers(init?.headers).get("Content-Type"),null);assert.ok(init?.body instanceof FormData);return Response.json({id:"file"});});
  const data=new FormData();data.append("file",new Blob(["test"]),"test.txt");await api("/files/upload",{method:"POST",body:data});
});

test("validation failures remain errors and expose field information",async()=>{
  mock.method(globalThis,"fetch",async()=>Response.json({detail:[{loc:["body","email"],msg:"adresse invalide"}]},{status:422}));
  await assert.rejects(mutate("/auth/login","POST",{email:"bad"}),e=>e instanceof ApiError&&e.status===422&&e.message.includes("email : adresse invalide"));
});

test("protected session expiry triggers the shell redirect event",async()=>{
  let expired=false;Object.defineProperty(globalThis,"window",{value:{dispatchEvent(event:Event){expired=event.type==="session-expired";}},configurable:true});
  mock.method(globalThis,"fetch",async()=>Response.json({detail:"Session expirée"},{status:401}));
  await assert.rejects(api("/documents"),ApiError);assert.equal(expired,true);
});

test("an invalid login does not trigger a protected-page redirect",async()=>{
  let expired=false;Object.defineProperty(globalThis,"window",{value:{dispatchEvent(){expired=true;}},configurable:true});
  mock.method(globalThis,"fetch",async()=>Response.json({detail:"Identifiants incorrects"},{status:401}));
  await assert.rejects(mutate("/auth/login","POST",{}),ApiError);assert.equal(expired,false);
});

test("204 deletion succeeds without parsing an empty body",async()=>{
  mock.method(globalThis,"fetch",async()=>new Response(null,{status:204}));assert.equal(await mutate("/community/posts/1","DELETE"),undefined);
});

test("network failure reports an actionable error instead of a false success",async()=>{
  mock.method(globalThis,"fetch",async()=>{throw new TypeError("Failed to fetch");});await assert.rejects(api("/documents"),e=>e instanceof ApiError&&e.status===0&&e.message.includes("Connexion au serveur impossible"));
});

test("CSRF cookie lookup does not match a similarly named cookie",()=>{
  assert.equal(csrfToken("other_campuspulse_csrf=wrong; campuspulse_csrf=right=="),"right==");assert.equal(csrfToken("other=123"),"");
});
