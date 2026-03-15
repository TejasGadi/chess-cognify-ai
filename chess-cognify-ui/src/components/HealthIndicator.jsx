import React, { useMemo } from 'react';
import { HeartPulse, RefreshCw, Database, ServerCog, Cpu, Loader2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import useHealthStore from '@/store/healthStore';

const SERVICE_GROUPS = [
    {
        label: 'Infrastructure',
        icon: Database,
        keys: ['postgresql', 'redis', 'qdrant'],
    },
    {
        label: 'AI Services',
        icon: ServerCog,
        keys: ['openai', 'ollama'],
    },
    {
        label: 'Engine',
        icon: Cpu,
        keys: ['stockfish'],
    },
];

const SERVICE_DISPLAY_NAMES = {
    postgresql: 'PostgreSQL',
    redis: 'Redis',
    qdrant: 'Qdrant',
    openai: 'OpenAI',
    ollama: 'Ollama',
    stockfish: 'Stockfish',
};

const statusColor = (status) => {
    switch (status) {
        case 'healthy':
            return 'bg-emerald-500';
        case 'degraded':
            return 'bg-amber-500';
        case 'unhealthy':
            return 'bg-red-500';
        default:
            return 'bg-muted-foreground/40';
    }
};

const statusTextColor = (status) => {
    switch (status) {
        case 'healthy':
            return 'text-emerald-500';
        case 'degraded':
            return 'text-amber-500';
        case 'unhealthy':
            return 'text-red-500';
        default:
            return 'text-muted-foreground';
    }
};

const StatusDot = ({ status, pulse = false, className }) => (
    <span className={cn('relative flex h-2.5 w-2.5', className)}>
        {pulse && status === 'unhealthy' && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
        )}
        <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', statusColor(status))} />
    </span>
);

const RelativeTime = ({ timestamp }) => {
    const [, setTick] = React.useState(0);

    React.useEffect(() => {
        const id = setInterval(() => setTick((t) => t + 1), 5000);
        return () => clearInterval(id);
    }, []);

    if (!timestamp) return <span>Never</span>;

    const seconds = Math.round((Date.now() - timestamp) / 1000);
    if (seconds < 5) return <span>Just now</span>;
    if (seconds < 60) return <span>{seconds}s ago</span>;
    const minutes = Math.floor(seconds / 60);
    return <span>{minutes}m ago</span>;
};

const PopoverBody = () => {
    const { overallStatus, services, requiredServices, lastChecked, isLoading, checkHealth } = useHealthStore();

    const handleRefresh = (e) => {
        e.stopPropagation();
        checkHealth();
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h4 className="font-semibold text-sm">System Health</h4>
                <button
                    onClick={handleRefresh}
                    disabled={isLoading}
                    className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors disabled:opacity-50"
                    aria-label="Refresh health status"
                >
                    <RefreshCw className={cn('h-3.5 w-3.5', isLoading && 'animate-spin')} />
                </button>
            </div>

            <div className="flex items-center gap-2">
                <StatusDot status={overallStatus} pulse />
                <span className={cn('text-xs font-medium capitalize', statusTextColor(overallStatus))}>
                    {overallStatus || 'Checking...'}
                </span>
            </div>

            <div className="space-y-3">
                {SERVICE_GROUPS.map((group) => {
                    const GroupIcon = group.icon;
                    const groupServices = group.keys.filter((k) => services[k]);
                    if (groupServices.length === 0 && Object.keys(services).length > 0) return null;

                    return (
                        <div key={group.label}>
                            <div className="flex items-center gap-1.5 mb-1.5">
                                <GroupIcon className="h-3 w-3 text-muted-foreground" />
                                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                    {group.label}
                                </span>
                            </div>
                            <div className="space-y-1 ml-[18px]">
                                {groupServices.length > 0 ? (
                                    groupServices.map((key) => {
                                        const svc = services[key];
                                        const isRequired = requiredServices.has(key);
                                        return (
                                            <TooltipProvider key={key} delayDuration={300}>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <div className={cn('flex items-center gap-2 py-0.5 cursor-default', !isRequired && 'opacity-50')}>
                                                            <StatusDot status={isRequired ? svc.status : (svc.status === 'healthy' ? 'healthy' : undefined)} />
                                                            <span className="text-xs">
                                                                {SERVICE_DISPLAY_NAMES[key] || key}
                                                            </span>
                                                            {!isRequired && (
                                                                <span className="ml-auto text-[9px] text-muted-foreground/60 italic">
                                                                    not in use
                                                                </span>
                                                            )}
                                                        </div>
                                                    </TooltipTrigger>
                                                    <TooltipContent side="right" className="max-w-[220px]">
                                                        <p className="text-xs">{svc.message}</p>
                                                        {!isRequired && (
                                                            <p className="text-xs text-muted-foreground mt-1">Not required by active model config</p>
                                                        )}
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        );
                                    })
                                ) : (
                                    <div className="flex items-center gap-2 py-0.5">
                                        <Loader2 className="h-2.5 w-2.5 animate-spin text-muted-foreground" />
                                        <span className="text-xs text-muted-foreground">Checking...</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="pt-2 border-t text-[10px] text-muted-foreground">
                Last checked: <RelativeTime timestamp={lastChecked} />
            </div>
        </div>
    );
};

const HealthIndicator = ({ variant = 'icon' }) => {
    const { overallStatus, isLoading, backendReachable } = useHealthStore();

    const displayStatus = useMemo(() => {
        if (backendReachable === false) return 'unhealthy';
        if (isLoading && !overallStatus) return null;
        return overallStatus;
    }, [backendReachable, isLoading, overallStatus]);

    if (variant === 'sidebar') {
        return (
            <Popover>
                <PopoverTrigger asChild>
                    <button className="w-full flex items-center gap-2 px-2 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent rounded-md transition-colors">
                        <div className="relative">
                            <HeartPulse className="h-4 w-4" />
                            {displayStatus && (
                                <StatusDot
                                    status={displayStatus}
                                    pulse
                                    className="absolute -top-0.5 -right-0.5 h-2 w-2 [&>span]:h-2 [&>span]:w-2"
                                />
                            )}
                        </div>
                        <span>System Health</span>
                    </button>
                </PopoverTrigger>
                <PopoverContent side="right" align="end" className="w-64">
                    <PopoverBody />
                </PopoverContent>
            </Popover>
        );
    }

    return (
        <Popover>
            <PopoverTrigger asChild>
                <button
                    className="relative p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors"
                    aria-label="System health status"
                >
                    <HeartPulse className={cn('w-5 h-5', statusTextColor(displayStatus))} />
                    {displayStatus && displayStatus !== 'healthy' && (
                        <StatusDot
                            status={displayStatus}
                            pulse
                            className="absolute top-1 right-1 h-2 w-2 [&>span]:h-2 [&>span]:w-2"
                        />
                    )}
                </button>
            </PopoverTrigger>
            <PopoverContent align="end" className="w-64">
                <PopoverBody />
            </PopoverContent>
        </Popover>
    );
};

export default HealthIndicator;
