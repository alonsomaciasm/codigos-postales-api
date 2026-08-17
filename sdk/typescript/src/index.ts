export interface MXPostalClientOptions {
  baseUrl?: string;
  apiKey?: string;
  token?: string;
  timeout?: number;
}

export interface Estado {
  clave_estado: string;
  nombre: string;
  nombre_sat?: string;
}

export interface Municipio {
  clave_municipio: string;
  nombre: string;
  nombre_sat?: string;
}

export interface Asentamiento {
  id: number;
  nombre: string;
  nombre_sat?: string;
  tipo_asentamiento: string;
  zona: string;
  codigo_postal: string;
  ciudad?: string;
  clave_estado: string;
  clave_municipio: string;
  latitud?: number;
  longitud?: number;
}

export interface ValidacionResult {
  es_valido: boolean;
  match_colonia?: boolean;
  match_estado?: boolean;
  match_municipio?: boolean;
  coincidencia_exacta: boolean;
  mensaje: string;
}

export interface CodigoPostalDetalle {
  codigo_postal: string;
  estado: Estado;
  municipio: Municipio;
  ciudad?: string;
  asentamientos: Asentamiento[];
  validacion?: ValidacionResult;
}

export interface AutocompleteItem {
  codigo_postal: string;
  estado_nombre: string;
  municipio_nombre: string;
  total_asentamientos: number;
}

export class MXPostalClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(options: MXPostalClientOptions = {}) {
    this.baseUrl = (options.baseUrl || 'http://localhost:8080').replace(/\/$/, '');
    this.timeout = options.timeout || 10000;
    this.headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    if (options.apiKey) {
      this.headers['X-API-Key'] = options.apiKey;
    }
    if (options.token) {
      this.headers['Authorization'] = `Bearer ${options.token}`;
    }
  }

  private async request<T>(path: string, params?: Record<string, any>, method = 'GET', body?: any): Promise<T> {
    const url = new URL(this.baseUrl + path);
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== undefined && params[key] !== null) {
          url.searchParams.append(key, String(params[key]));
        }
      });
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url.toString(), {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `HTTP Error ${response.status}`);
      }

      return await response.json();
    } catch (err: any) {
      clearTimeout(timeoutId);
      throw new Error(`MXPostalClient Error: ${err.message}`);
    }
  }

  public async getCodigoPostal(
    cp: string,
    options?: { colonia?: string; estado?: string; municipio?: string }
  ): Promise<CodigoPostalDetalle> {
    return this.request<CodigoPostalDetalle>(`/api/v1/codigo-postal/${cp}`, options);
  }

  public async batchValidate(items: Array<{ id_externo?: string; codigo_postal: string; colonia?: string; estado?: string; municipio?: string }>): Promise<any[]> {
    return this.request<any[]>('/api/v1/codigo-postal/batch-validate', undefined, 'POST', items);
  }

  public async getGeoJSON(cp: string): Promise<any> {
    return this.request<any>(`/api/v1/codigo-postal/${cp}/geojson`);
  }

  public async autocomplete(prefix: string, limit = 10): Promise<AutocompleteItem[]> {
    return this.request<AutocompleteItem[]>('/api/v1/codigo-postal/autocomplete', { prefix, limit });
  }

  public async buscarCercanos(lat: number, lng: number, radioKm = 5.0, limit = 10): Promise<Asentamiento[]> {
    return this.request<Asentamiento[]>('/api/v1/codigo-postal/cercanos', { lat, lng, radio_km: radioKm, limit });
  }

  public async getEstados(): Promise<Estado[]> {
    return this.request<Estado[]>('/api/v1/estados');
  }

  public async getMunicipios(claveEstado: string): Promise<Municipio[]> {
    return this.request<Municipio[]>(`/api/v1/estados/${claveEstado}/municipios`);
  }

  public async getEstadoGeoJSON(claveEstado: string): Promise<any> {
    return this.request<any>(`/api/v1/estados/${claveEstado}/geojson`);
  }

  public async getEstadoPDF(claveEstado: string, options?: { titulo?: string; subtitulo?: string; logoUrl?: string }): Promise<Blob> {
    const params: Record<string, any> = {};
    if (options?.titulo) params.titulo = options.titulo;
    if (options?.subtitulo) params.subtitulo = options.subtitulo;
    if (options?.logoUrl) params.logo_url = options.logoUrl;

    const url = new URL(`${this.baseUrl}/api/v1/estados/${claveEstado}/pdf`);
    Object.keys(params).forEach(k => url.searchParams.append(k, params[k]));

    const res = await fetch(url.toString(), { headers: this.headers });
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    return await res.blob();
  }

  public async getStats(): Promise<any> {
    return this.request<any>('/api/v1/stats');
  }
}
