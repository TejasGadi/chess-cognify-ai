import React, { useState, useEffect } from 'react';
import {
    Cpu,
    Database,
    Eye,
    Save,
    CheckCircle2,
    AlertCircle,
    RefreshCw,
    Server,
    Key,
    Globe
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { toast } from "sonner";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const ModelSettings = () => {
    const showToast = ({ title, description, variant, duration }) => {
        const options = { description };
        if (duration) options.duration = duration;
        if (variant === 'destructive') toast.error(title, options);
        else toast.success(title, options);
    };
    const [providers, setProviders] = useState([]);
    const [activeModels, setActiveModels] = useState({ llm: null, embedding: null, vision: null });
    const [isLoading, setIsLoading] = useState(true);

    // Config state
    const [selectedType, setSelectedType] = useState('llm'); // llm, embedding, vision
    const [selectedProvider, setSelectedProvider] = useState(null);
    const [formData, setFormData] = useState({});
    const [isSaving, setIsSaving] = useState(false);
    const [isTesting, setIsTesting] = useState(false);
    const [testResult, setTestResult] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setIsLoading(true);
        try {
            // Fetch providers metadata
            const provRes = await fetch(`${API_BASE_URL}/api/model-config/providers`);
            if (provRes.ok) {
                const provData = await provRes.json();
                setProviders(provData);
            }

            // Fetch active configs
            const activeRes = await fetch(`${API_BASE_URL}/api/model-config/active`);
            if (activeRes.ok) {
                const activeData = await activeRes.json();
                setActiveModels(activeData);

                // Pre-select the active provider for the current tab
                if (activeData.llm) {
                    handleProviderSelect('llm', activeData.llm.provider, activeData.llm);
                }
            }
        } catch (error) {
            console.error('Error fetching model settings:', error);
            showToast({
                title: 'Error formatting settings',
                description: 'Failed to load model configurations',
                variant: 'destructive',
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleTypeChange = (type) => {
        setSelectedType(type);
        setTestResult(null);

        // Auto-select active provider for this type if one exists
        const activeConfig = activeModels[type];
        if (activeConfig) {
            handleProviderSelect(type, activeConfig.provider, activeConfig);
        } else {
            setSelectedProvider(null);
            setFormData({});
        }
    };

    const handleProviderSelect = (type, providerId, existingConfig = null) => {
        const provider = providers.find(p => p.id === providerId);
        if (!provider) return;

        setSelectedProvider(provider);

        // Find default model based on type
        let defaultModel = '';
        if (type === 'llm' && provider.default_llm_models?.length) defaultModel = provider.default_llm_models[0];
        if (type === 'embedding' && provider.default_embedding_models?.length) defaultModel = provider.default_embedding_models[0];
        if (type === 'vision' && provider.default_vision_models?.length) defaultModel = provider.default_vision_models[0];

        setFormData({
            model_name: existingConfig?.model_name || defaultModel,
            api_key: existingConfig?.api_key_masked === '****' ? '' : (existingConfig?.api_key_masked || ''),
            api_base: existingConfig?.api_base || '',
        });

        setTestResult(null);
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleTestConnection = async () => {
        if (!selectedProvider) return;

        // Basic validation
        if (selectedProvider.id !== 'ollama' && !formData.api_key && activeModels[selectedType]?.api_key_masked === '****') {
            // we have an existing masked key, we can test it using the backend DB key
        } else if (selectedProvider.id !== 'ollama' && !formData.api_key) {
            showToast({ title: 'Missing API Key', description: 'Please provide an API key to test.', variant: 'destructive' });
            return;
        }

        setIsTesting(true);
        setTestResult(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/model-config/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: selectedProvider.id,
                    model_name: formData.model_name,
                    api_key: formData.api_key || undefined, // If empty, backend will try to use existing
                    api_base: formData.api_base || undefined,
                    config_type: selectedType
                })
            });

            const data = await res.json();
            setTestResult(data);

            if (data.success) {
                showToast({ title: 'Connection Successful', description: data.message });
            } else {
                showToast({ title: 'Connection Failed', description: data.message, variant: 'destructive' });
            }
        } catch (error) {
            setTestResult({ success: false, message: error.message });
            showToast({ title: 'Error', description: 'Failed to complete test', variant: 'destructive' });
        } finally {
            setIsTesting(false);
        }
    };

    const handleSaveAndActivate = async () => {
        if (!selectedProvider) return;

        setIsSaving(true);
        try {
            // First, create or update the config
            const saveRes = await fetch(`${API_BASE_URL}/api/model-config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    config_type: selectedType,
                    provider: selectedProvider.id,
                    model_name: formData.model_name,
                    api_key: formData.api_key || undefined,
                    api_base: formData.api_base || undefined
                })
            });

            if (!saveRes.ok) throw new Error('Failed to save configuration');
            const savedConfig = await saveRes.json();

            // Then, activate it
            const activateRes = await fetch(`${API_BASE_URL}/api/model-config/${savedConfig.id}/activate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!activateRes.ok) throw new Error('Failed to activate configuration');
            const activatedConfig = await activateRes.json();

            // Update local state
            setActiveModels(prev => ({ ...prev, [selectedType]: activatedConfig }));

            showToast({
                title: 'Configuration Saved',
                description: `Successfully activated ${selectedProvider.name} for ${selectedType} models.`,
            });

            // If they changed the embedding model, show warning
            if (selectedType === 'embedding') {
                showToast({
                    title: 'Embedding Model Changed',
                    description: 'Your existing chess books need to be re-indexed with the new model. This will happen in the background.',
                    duration: 8000,
                });
            }

            setFormData(prev => ({ ...prev, api_key: '' })); // clear input

        } catch (error) {
            console.error('Save error:', error);
            showToast({
                title: 'Error Saving',
                description: error.message,
                variant: 'destructive',
            });
        } finally {
            setIsSaving(false);
        }
    };

    // Filter providers based on the selected type capability
    const availableProviders = providers.filter(p => {
        if (selectedType === 'llm') return p.supports_llm;
        if (selectedType === 'embedding') return p.supports_embedding;
        if (selectedType === 'vision') return p.supports_vision;
        return false;
    });

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center p-8 bg-background">
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                    <RefreshCw className="h-8 w-8 animate-spin" />
                    <p>Loading configurations...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-auto bg-background/50 p-6">
            <div className="mx-auto max-w-5xl space-y-8">

                {/* Header */}
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">AI Model Setup</h1>
                    <p className="text-muted-foreground mt-2">
                        Configure the intelligence engine behind Chess Cognify. Connect to local or cloud AI providers.
                    </p>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 p-1 bg-muted/40 rounded-lg w-fit">
                    <button
                        onClick={() => handleTypeChange('llm')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2
                            ${selectedType === 'llm' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}
                    >
                        <Cpu className="w-4 h-4" />
                        Analysis Engine (LLM)
                    </button>
                    <button
                        onClick={() => handleTypeChange('vision')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2
                            ${selectedType === 'vision' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}
                    >
                        <Eye className="w-4 h-4" />
                        Vision Model
                    </button>
                    <button
                        onClick={() => handleTypeChange('embedding')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center gap-2
                            ${selectedType === 'embedding' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}
                    >
                        <Database className="w-4 h-4" />
                        Book Embeddings
                    </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                    {/* Left Column: Provider Selection */}
                    <div className="lg:col-span-5 space-y-4">
                        <h3 className="text-lg font-medium">Select Provider</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {availableProviders.map(provider => {
                                const isActive = activeModels[selectedType]?.provider === provider.id;
                                const isSelected = selectedProvider?.id === provider.id;

                                return (
                                    <button
                                        key={provider.id}
                                        onClick={() => handleProviderSelect(selectedType, provider.id, isActive ? activeModels[selectedType] : null)}
                                        className={`relative p-4 rounded-xl border-2 text-left flex flex-col gap-2 transition-all
                                            ${isSelected ? 'border-primary bg-primary/5 ring-4 ring-primary/10' : 'border-border/50 bg-card hover:border-primary/50 hover:bg-accent/50'}
                                        `}
                                    >
                                        {isActive && (
                                            <Badge variant="default" className="absolute -top-2 -right-2 px-1.5 py-0.5 text-[10px]">
                                                Active
                                            </Badge>
                                        )}
                                        <div className="flex items-center gap-2 font-semibold">
                                            {provider.name}
                                        </div>
                                        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                            {provider.description}
                                        </p>
                                    </button>
                                );
                            })}
                        </div>

                        {selectedType === 'embedding' && (
                            <Alert variant="warning" className="bg-amber-500/10 text-amber-600 dark:text-amber-500 border-amber-500/20 mt-6 flex flex-col gap-1 items-start text-left">
                                <div className="flex items-center gap-2">
                                    <AlertCircle className="h-4 w-4 shrink-0" />
                                    <AlertTitle className="m-0 text-sm font-semibold">Changing Embedding Models</AlertTitle>
                                </div>
                                <AlertDescription className="text-xs mt-1 leading-relaxed pl-6">
                                    If you change your embedding provider, all existing vectors in your chess library will be invalidated. The system will automatically re-index your PDF books to ensure search works properly.
                                </AlertDescription>
                            </Alert>
                        )}
                    </div>

                    {/* Right Column: Configuration Form */}
                    <div className="lg:col-span-7">
                        {!selectedProvider ? (
                            <Card className="h-full border-dashed bg-muted/20 flex items-center justify-center py-16">
                                <CardContent className="flex flex-col items-center text-center text-muted-foreground pt-6">
                                    <Server className="h-10 w-10 mb-4 opacity-20" />
                                    <p>Select a provider from the left to configure it.</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="overflow-hidden shadow-sm">
                                <CardHeader className="bg-muted/30 border-b">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <CardTitle className="text-xl flex items-center gap-2">
                                                {selectedProvider.name} Settings
                                                {activeModels[selectedType]?.provider === selectedProvider.id && (
                                                    <Badge variant="outline" className="ml-2 font-normal text-green-600 border-green-600/30 bg-green-600/10">Currently Active</Badge>
                                                )}
                                            </CardTitle>
                                            <CardDescription className="mt-1">
                                                Configure connection details for {selectedType} models.
                                            </CardDescription>
                                        </div>
                                    </div>
                                </CardHeader>

                                <CardContent className="space-y-6 pt-6">
                                    {/* Model Selection */}
                                    <div className="space-y-2">
                                        <Label htmlFor="model_name">Model Name</Label>
                                        <Input
                                            id="model_name"
                                            value={formData.model_name || ''}
                                            onChange={(e) => handleInputChange('model_name', e.target.value)}
                                            placeholder="e.g. gpt-4o"
                                            className="font-mono text-sm"
                                        />

                                        <div className="flex flex-wrap gap-1.5 mt-2">
                                            {(selectedType === 'llm' ? selectedProvider.default_llm_models :
                                                selectedType === 'embedding' ? selectedProvider.default_embedding_models :
                                                    selectedProvider.default_vision_models)?.map(model => (
                                                        <Badge
                                                            key={model}
                                                            variant={formData.model_name === model ? "secondary" : "outline"}
                                                            className="cursor-pointer font-normal text-[10px]"
                                                            onClick={() => handleInputChange('model_name', model)}
                                                        >
                                                            {model}
                                                        </Badge>
                                                    ))}
                                        </div>
                                    </div>

                                    {/* Dynamic Fields (API Key, Base URL) */}
                                    {selectedProvider.fields.map(field => (
                                        <div key={field.name} className="space-y-2">
                                            <Label htmlFor={field.name} className="flex gap-2">
                                                {field.type === 'password' ? <Key className="w-4 h-4 text-muted-foreground" /> : <Globe className="w-4 h-4 text-muted-foreground" />}
                                                {field.label}
                                                {!field.required && <span className="text-muted-foreground font-normal">(Optional)</span>}
                                            </Label>

                                            <Input
                                                id={field.name}
                                                type={field.type === 'password' && formData[field.name]?.includes('****') ? 'text' : field.type}
                                                value={formData[field.name] || ''}
                                                onChange={(e) => handleInputChange(field.name, e.target.value)}
                                                placeholder={field.placeholder}
                                                className={`font-mono text-sm ${field.type === 'password' ? 'text-primary' : ''}`}
                                            />
                                            {field.help_text && (
                                                <p className="text-xs text-muted-foreground">{field.help_text}</p>
                                            )}
                                            {field.type === 'password' && activeModels[selectedType]?.provider === selectedProvider.id && (
                                                <p className="text-[10px] text-muted-foreground">
                                                    A key is stored securely. Enter a new one to overwrite.
                                                </p>
                                            )}
                                        </div>
                                    ))}

                                    {/* Test Result */}
                                    {testResult && (
                                        <Alert variant={testResult.success ? "default" : "destructive"}
                                            className={testResult.success ? "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20" : ""}>
                                            {testResult.success ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                                            <AlertTitle>{testResult.success ? "Connection Verified" : "Test Failed"}</AlertTitle>
                                            <AlertDescription className="text-xs break-all font-mono mt-1">
                                                {testResult.message}
                                            </AlertDescription>
                                        </Alert>
                                    )}
                                </CardContent>

                                <CardFooter className="bg-muted/10 border-t py-4 flex justify-between">
                                    <Button
                                        variant="outline"
                                        onClick={handleTestConnection}
                                        disabled={isTesting || !formData.model_name}
                                    >
                                        {isTesting ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Cpu className="mr-2 h-4 w-4" />}
                                        Test Connection
                                    </Button>
                                    <Button
                                        onClick={handleSaveAndActivate}
                                        disabled={isSaving || !formData.model_name}
                                    >
                                        {isSaving ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                                        Save & Activate
                                    </Button>
                                </CardFooter>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ModelSettings;
