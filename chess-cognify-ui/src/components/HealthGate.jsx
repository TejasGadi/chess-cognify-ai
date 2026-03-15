import React, { useEffect, useState, useRef, useMemo } from 'react';
import { ServerCrash, AlertTriangle, RefreshCw, Loader2, CircleX, CircleCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import useHealthStore from '@/store/healthStore';

const AUTO_RETRY_SECONDS = 10;

const SERVICE_DISPLAY_NAMES = {
    postgresql: 'PostgreSQL',
    redis: 'Redis',
    qdrant: 'Qdrant',
    openai: 'OpenAI',
    ollama: 'Ollama',
    stockfish: 'Stockfish',
};

const HealthGate = ({ children }) => {
    const {
        backendReachable, overallStatus, services, requiredServices, isLoading,
        checkHealth, startPolling, stopPolling,
    } = useHealthStore();
    const [countdown, setCountdown] = useState(AUTO_RETRY_SECONDS);
    const [retrying, setRetrying] = useState(false);
    const countdownRef = useRef(null);

    const unhealthyRequired = useMemo(() => {
        return Object.entries(services)
            .filter(([key, svc]) => requiredServices.has(key) && svc.status === 'unhealthy')
            .map(([key, svc]) => ({ key, name: SERVICE_DISPLAY_NAMES[key] || key, message: svc.message }));
    }, [services, requiredServices]);

    const shouldBlock = backendReachable === false || unhealthyRequired.length > 0;

    useEffect(() => {
        startPolling(30000);
        return () => stopPolling();
    }, [startPolling, stopPolling]);

    useEffect(() => {
        if (!shouldBlock) {
            if (countdownRef.current) clearInterval(countdownRef.current);
            return;
        }

        setCountdown(AUTO_RETRY_SECONDS);
        countdownRef.current = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    checkHealth();
                    return AUTO_RETRY_SECONDS;
                }
                return prev - 1;
            });
        }, 1000);

        return () => {
            if (countdownRef.current) clearInterval(countdownRef.current);
        };
    }, [shouldBlock, checkHealth]);

    const handleRetry = async () => {
        setRetrying(true);
        await checkHealth();
        setRetrying(false);
        setCountdown(AUTO_RETRY_SECONDS);
    };

    if (backendReachable === null && isLoading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-sm font-medium">Connecting to server...</p>
                </div>
            </div>
        );
    }

    if (backendReachable === false) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-background p-6">
                <Card className="w-full max-w-md text-center">
                    <CardContent className="pt-10 pb-8 flex flex-col items-center gap-5">
                        <div className="rounded-full bg-destructive/10 p-4">
                            <ServerCrash className="h-12 w-12 text-destructive" />
                        </div>

                        <div className="space-y-2">
                            <h1 className="text-2xl font-bold tracking-tight">Backend Unavailable</h1>
                            <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                                The server is not responding. Make sure the backend is running.
                            </p>
                        </div>

                        <RetryFooter
                            retrying={retrying}
                            countdown={countdown}
                            onRetry={handleRetry}
                        />
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (unhealthyRequired.length > 0) {
        const allRequiredDown = unhealthyRequired.length >= requiredServices.size;
        return (
            <div className="flex h-screen w-full items-center justify-center bg-background p-6">
                <Card className="w-full max-w-lg text-center">
                    <CardContent className="pt-10 pb-8 flex flex-col items-center gap-5">
                        <div className={`rounded-full p-4 ${allRequiredDown ? 'bg-destructive/10' : 'bg-amber-500/10'}`}>
                            {allRequiredDown
                                ? <ServerCrash className="h-12 w-12 text-destructive" />
                                : <AlertTriangle className="h-12 w-12 text-amber-500" />
                            }
                        </div>

                        <div className="space-y-2">
                            <h1 className="text-2xl font-bold tracking-tight">
                                {allRequiredDown ? 'Services Unavailable' : 'Services Degraded'}
                            </h1>
                            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                                {unhealthyRequired.length === 1
                                    ? `${unhealthyRequired[0].name} is not running. The app cannot function without it.`
                                    : `${unhealthyRequired.map(s => s.name).join(', ')} are not running. Start these services to use the app.`
                                }
                            </p>
                        </div>

                        <div className="w-full max-w-xs mx-auto text-left space-y-1.5">
                            {Object.entries(services).map(([key, svc]) => {
                                const isRequired = requiredServices.has(key);
                                const isDown = svc.status === 'unhealthy';
                                return (
                                    <div key={key} className={`flex items-center gap-2.5 rounded-md px-3 py-1.5 ${isRequired ? 'bg-muted/50' : 'bg-muted/20 opacity-60'}`}>
                                        {isDown
                                            ? <CircleX className={`h-4 w-4 shrink-0 ${isRequired ? 'text-red-500' : 'text-muted-foreground'}`} />
                                            : <CircleCheck className="h-4 w-4 text-emerald-500 shrink-0" />
                                        }
                                        <span className={`text-sm ${isDown && isRequired ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                                            {SERVICE_DISPLAY_NAMES[key] || key}
                                        </span>
                                        {isDown && isRequired && (
                                            <span className="ml-auto text-[10px] text-red-400 font-medium uppercase tracking-wide">
                                                Down
                                            </span>
                                        )}
                                        {!isRequired && (
                                            <span className="ml-auto text-[10px] text-muted-foreground/50 uppercase tracking-wide">
                                                Optional
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        <RetryFooter
                            retrying={retrying}
                            countdown={countdown}
                            onRetry={handleRetry}
                        />
                    </CardContent>
                </Card>
            </div>
        );
    }

    return children;
};

const RetryFooter = ({ retrying, countdown, onRetry }) => (
    <>
        <Button onClick={onRetry} disabled={retrying} className="mt-2">
            {retrying
                ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                : <RefreshCw className="mr-2 h-4 w-4" />
            }
            {retrying ? 'Retrying...' : 'Retry Now'}
        </Button>
        <p className="text-xs text-muted-foreground">
            Auto-retrying in {countdown}s
        </p>
    </>
);

export default HealthGate;
