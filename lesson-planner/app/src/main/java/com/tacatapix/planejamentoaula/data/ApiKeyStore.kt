package com.tacatapix.planejamentoaula.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "settings")

class ApiKeyStore(private val context: Context) {
    private val apiKey = stringPreferencesKey("openai_api_key")

    val apiKeyFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[apiKey].orEmpty()
    }

    suspend fun setApiKey(value: String) {
        context.dataStore.edit { prefs ->
            prefs[apiKey] = value.trim()
        }
    }
}
