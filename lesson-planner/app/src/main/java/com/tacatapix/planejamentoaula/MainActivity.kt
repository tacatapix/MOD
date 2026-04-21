package com.tacatapix.planejamentoaula

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.tacatapix.planejamentoaula.ui.screens.FormScreen
import com.tacatapix.planejamentoaula.ui.screens.SettingsScreen
import com.tacatapix.planejamentoaula.ui.theme.PlanejamentoAulaTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            PlanejamentoAulaTheme {
                var showSettings by remember { mutableStateOf(false) }
                if (showSettings) {
                    SettingsScreen(onBack = { showSettings = false })
                } else {
                    FormScreen(onOpenSettings = { showSettings = true })
                }
            }
        }
    }
}
