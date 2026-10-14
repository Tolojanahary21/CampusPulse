import test from "node:test";import assert from "node:assert/strict";import {canRole,params} from "../src/lib/format.ts";
test("a campus administrator sees management actions only in the assigned campus",()=>{
 const user={roles:[{role:"CAMPUS_ADMIN",campus_id:"campus-a"}]};assert.equal(canRole(user,["CAMPUS_ADMIN"],"campus-a"),true);assert.equal(canRole(user,["CAMPUS_ADMIN"],"campus-b"),false);assert.equal(canRole(user,[],"campus-a"),false);
});
test("a student never receives publication controls from membership alone",()=>{assert.equal(canRole({roles:[{role:"STUDENT",campus_id:"a"}]},["CONTENT_PUBLISHER","CAMPUS_ADMIN"],"a"),false);});
test("a global administrator has access across campuses",()=>{assert.equal(canRole({roles:[{role:"PLATFORM_ADMIN",campus_id:null}]},["CAMPUS_ADMIN"],"b"),true);});
test("query filters keep false and zero and escape search input",()=>{assert.equal(params({q:"A&B",page:0,manage:false,campus_id:undefined,status:""}),"?q=A%26B&page=0&manage=false");});
