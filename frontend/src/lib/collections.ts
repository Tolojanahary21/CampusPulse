import { api } from "./api";
import type { Collection, RecordItem } from "@/types";

/** Reference selectors follow pagination so no campus or academic option is lost. */
export async function allItems<T = RecordItem>(path: string): Promise<Collection<T>> {
  const items:T[]=[];
  let page=1;
  let result:Collection<T>;
  do {
    result=await api<Collection<T>>(`${path}${path.includes("?")?"&":"?"}page=${page}&page_size=100`);
    items.push(...result.items);
    page+=1;
  } while(result.items.length>0&&items.length<result.total);
  return {items,total:items.length,page:1,page_size:items.length};
}
