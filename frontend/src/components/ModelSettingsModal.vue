<template>
  <div v-if="open" class="modal-backdrop">
    <section class="model-modal">
      <div class="panel-header">
        <div>
          <h2>Model Settings</h2>
          <p>OpenAI-compatible providers and default assessment model.</p>
        </div>
        <button class="icon-button" type="button" @click="$emit('close')">Close</button>
      </div>

      <p v-if="error" class="error-message">{{ error }}</p>
      <p v-if="notice" class="success-message">{{ notice }}</p>

      <div class="settings-grid">
        <form class="settings-form" @submit.prevent="saveProvider">
          <h3>Provider</h3>
          <label>
            <span>Name</span>
            <input v-model="providerForm.name" required />
          </label>
          <label>
            <span>Base URL</span>
            <input v-model="providerForm.base_url" placeholder="https://api.openai.com/v1" required />
          </label>
          <label>
            <span>API key env var</span>
            <input v-model="providerForm.api_key_secret_ref" placeholder="OPENAI_API_KEY" />
          </label>
          <button class="query-submit" type="submit">Save Provider</button>
        </form>

        <form class="settings-form" @submit.prevent="saveModel">
          <h3>Model</h3>
          <label>
            <span>Provider</span>
            <select v-model="modelForm.provider_id" required>
              <option value="" disabled>Select provider</option>
              <option v-for="provider in configs.providers" :key="provider.provider_id" :value="provider.provider_id">
                {{ provider.name }}
              </option>
            </select>
          </label>
          <label>
            <span>Model name</span>
            <input v-model="modelForm.model_name" placeholder="gpt-4.1-mini" required />
          </label>
          <label>
            <span>Timeout seconds</span>
            <input v-model.number="modelForm.timeout_seconds" type="number" min="1" />
          </label>
          <label class="checkbox-row">
            <input v-model="modelForm.is_default" type="checkbox" />
            <span>Set as default</span>
          </label>
          <button class="query-submit" type="submit">Save Model</button>
        </form>
      </div>

      <div class="model-list">
        <div v-for="model in configs.models" :key="model.model_id" class="model-row">
          <div>
            <strong>{{ model.model_name }}</strong>
            <span>{{ providerName(model.provider_id) }} · {{ model.is_default ? 'default' : 'available' }}</span>
          </div>
          <button type="button" @click="makeDefault(model.model_id)">Default</button>
          <button type="button" @click="testModel(model.model_id)">Test</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { createModel, createProvider, fetchModelConfigs, setDefaultModel, testModelConnection } from '../services/modelConfigApi'

const props = defineProps({
  open: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['close'])
const configs = reactive({ providers: [], models: [] })
const error = ref('')
const notice = ref('')
const providerForm = reactive({
  name: 'OpenAI Compatible',
  provider_type: 'openai-compatible',
  base_url: '',
  api_key_secret_ref: '',
  enabled: true
})
const modelForm = reactive({
  provider_id: '',
  model_name: '',
  temperature: 0.2,
  max_tokens: 1200,
  timeout_seconds: 30,
  is_default: true
})

watch(
  () => props.open,
  (open) => {
    if (open) loadConfigs()
  }
)

async function loadConfigs() {
  error.value = ''
  notice.value = ''
  try {
    const data = await fetchModelConfigs()
    configs.providers = data.providers
    configs.models = data.models
    if (!modelForm.provider_id && configs.providers[0]) {
      modelForm.provider_id = configs.providers[0].provider_id
    }
  } catch (err) {
    error.value = err.message
  }
}

async function saveProvider() {
  try {
    const provider = await createProvider(providerForm)
    notice.value = 'Provider saved.'
    await loadConfigs()
    modelForm.provider_id = provider.provider_id
  } catch (err) {
    error.value = err.message
  }
}

async function saveModel() {
  try {
    await createModel(modelForm)
    notice.value = 'Model saved.'
    await loadConfigs()
  } catch (err) {
    error.value = err.message
  }
}

async function makeDefault(modelId) {
  try {
    await setDefaultModel(modelId)
    notice.value = 'Default model updated.'
    await loadConfigs()
  } catch (err) {
    error.value = err.message
  }
}

async function testModel(modelId) {
  try {
    const result = await testModelConnection(modelId)
    notice.value = result.message
  } catch (err) {
    error.value = err.message
  }
}

function providerName(providerId) {
  return configs.providers.find((provider) => provider.provider_id === providerId)?.name ?? 'Unknown provider'
}
</script>
