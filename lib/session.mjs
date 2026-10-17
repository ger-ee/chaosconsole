import {randomBytes,createCipheriv,createDecipheriv} from 'node:crypto';
export function seal(value,key){const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',Buffer.from(key,'hex'),iv);const data=Buffer.concat([cipher.update(JSON.stringify(value)),cipher.final()]);return Buffer.concat([iv,cipher.getAuthTag(),data]).toString('base64url');}
export function unseal(value,key){try{const b=Buffer.from(value||'','base64url'),d=createDecipheriv('aes-256-gcm',Buffer.from(key,'hex'),b.subarray(0,12));d.setAuthTag(b.subarray(12,28));const v=JSON.parse(Buffer.concat([d.update(b.subarray(28)),d.final()]));return v.exp>Date.now()?v:null;}catch{return null;}}
export function cookies(req){return Object.fromEntries((req.headers.cookie||'').split(';').map(v=>v.trim().split('=')));}
export const cookie=(name,value,age=3600)=>`${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${age}`;
