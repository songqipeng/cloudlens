export interface Resource {
  id: string
  name?: string
  type?: string
  status?: string
  region?: string
  instanceType?: string
  cost?: number
  [key: string]: any
}



