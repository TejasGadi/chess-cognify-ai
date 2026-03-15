import { create } from 'zustand';
import api from '../lib/api';

const ALWAYS_REQUIRED = ['postgresql', 'redis', 'qdrant', 'stockfish'];

const PROVIDER_TO_SERVICE = {
    openai: 'openai',
    ollama: 'ollama',
};

const useHealthStore = create((set, get) => ({
    backendReachable: null,
    overallStatus: null,
    services: {},
    requiredServices: new Set(ALWAYS_REQUIRED),
    activeProviders: {},
    lastChecked: null,
    isLoading: true,
    error: null,
    _intervalId: null,

    checkHealth: async () => {
        set({ isLoading: true, error: null });

        try {
            await api.get('/health', { timeout: 5000 });
        } catch {
            set({
                backendReachable: false,
                overallStatus: null,
                services: {},
                lastChecked: Date.now(),
                isLoading: false,
                error: 'Backend is not reachable',
            });
            return;
        }

        set({ backendReachable: true });

        const [statusResult, configResult] = await Promise.allSettled([
            api.get('/api/status', { timeout: 10000 }),
            api.get('/api/model-config/active', { timeout: 5000 }),
        ]);

        let services = {};
        let overallStatus = 'unknown';
        if (statusResult.status === 'fulfilled') {
            services = statusResult.value.data.services || {};
            overallStatus = statusResult.value.data.status;
        }

        const required = new Set(ALWAYS_REQUIRED);
        let activeProviders = {};
        if (configResult.status === 'fulfilled') {
            activeProviders = configResult.value.data || {};
            const providerIds = new Set();
            for (const cfg of Object.values(activeProviders)) {
                if (cfg?.provider) providerIds.add(cfg.provider);
            }
            if (providerIds.size === 0) {
                required.add('openai');
            } else {
                for (const pid of providerIds) {
                    const svcName = PROVIDER_TO_SERVICE[pid];
                    if (svcName) required.add(svcName);
                }
            }
        } else {
            required.add('openai');
        }

        const requiredUnhealthy = Object.entries(services)
            .filter(([key, svc]) => required.has(key) && svc.status === 'unhealthy');

        let effectiveStatus = overallStatus;
        if (requiredUnhealthy.length > 0) {
            effectiveStatus = requiredUnhealthy.length >= required.size ? 'unhealthy' : 'degraded';
        } else {
            effectiveStatus = 'healthy';
        }

        set({
            overallStatus: effectiveStatus,
            services,
            requiredServices: required,
            activeProviders,
            lastChecked: Date.now(),
            isLoading: false,
        });
    },

    startPolling: (intervalMs = 30000) => {
        const { _intervalId, checkHealth } = get();
        if (_intervalId) return;

        checkHealth();

        const id = setInterval(() => {
            checkHealth();
        }, intervalMs);
        set({ _intervalId: id });
    },

    stopPolling: () => {
        const { _intervalId } = get();
        if (_intervalId) {
            clearInterval(_intervalId);
            set({ _intervalId: null });
        }
    },
}));

export default useHealthStore;
