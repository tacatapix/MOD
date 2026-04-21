package com.tacatapix.planejamentoaula.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import com.tacatapix.planejamentoaula.ai.BnccResposta
import com.tacatapix.planejamentoaula.ai.OpenAIClient
import com.tacatapix.planejamentoaula.data.ApiKeyStore
import com.tacatapix.planejamentoaula.data.LessonPlan
import com.tacatapix.planejamentoaula.data.lessonPlanFields
import com.tacatapix.planejamentoaula.pdf.PdfExporter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FormScreen(
    onOpenSettings: () -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val apiKeyStore = remember { ApiKeyStore(context) }
    val openAI = remember { OpenAIClient() }

    var plan by remember { mutableStateOf(LessonPlan()) }
    var loadingBncc by remember { mutableStateOf(false) }
    var exportingPdf by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Planejamento de Aula") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                ),
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Ajustes")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(lessonPlanFields) { field ->
                OutlinedTextField(
                    value = field.getter(plan),
                    onValueChange = { plan = field.setter(plan, it) },
                    label = { Text(field.label) },
                    placeholder = { Text(field.placeholder) },
                    singleLine = field.singleLine,
                    minLines = if (field.singleLine) 1 else 3,
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(
                        capitalization = KeyboardCapitalization.Sentences
                    )
                )
            }

            item {
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            scope.launch {
                                val key = apiKeyStore.apiKeyFlow.first()
                                if (key.isBlank()) {
                                    snackbarHostState.showSnackbar(
                                        "Configure a chave da API OpenAI em Ajustes."
                                    )
                                    return@launch
                                }
                                loadingBncc = true
                                val result = openAI.gerarBncc(key, plan)
                                loadingBncc = false
                                result.fold(
                                    onSuccess = { resposta -> plan = aplicarBncc(plan, resposta) },
                                    onFailure = { e ->
                                        snackbarHostState.showSnackbar(
                                            "Falha ao gerar BNCC: ${e.message}"
                                        )
                                    }
                                )
                            }
                        },
                        enabled = !loadingBncc,
                        modifier = Modifier.weight(1f)
                    ) {
                        if (loadingBncc) {
                            CircularProgressIndicator(
                                modifier = Modifier.height(18.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null)
                        }
                        Spacer(Modifier.height(0.dp))
                        Text("  Gerar BNCC")
                    }

                    Button(
                        onClick = {
                            scope.launch {
                                exportingPdf = true
                                runCatching {
                                    val file = PdfExporter.exportarParaPdf(context, plan)
                                    PdfExporter.compartilhar(context, file)
                                    snackbarHostState.showSnackbar(
                                        "PDF gerado: ${file.name}"
                                    )
                                }.onFailure { e ->
                                    snackbarHostState.showSnackbar(
                                        "Falha ao exportar PDF: ${e.message}"
                                    )
                                }
                                exportingPdf = false
                            }
                        },
                        enabled = !exportingPdf,
                        modifier = Modifier.weight(1f)
                    ) {
                        if (exportingPdf) {
                            CircularProgressIndicator(
                                modifier = Modifier.height(18.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.PictureAsPdf, contentDescription = null)
                        }
                        Text("  Exportar PDF")
                    }
                }
                Spacer(Modifier.height(16.dp))
            }
        }
    }

    // Pré-condição: em primeiro acesso, avisa se a chave não foi configurada
    LaunchedEffect(Unit) {
        val key = apiKeyStore.apiKeyFlow.first()
        if (key.isBlank()) {
            snackbarHostState.showSnackbar(
                "Configure a chave da OpenAI em Ajustes para ativar a geração de BNCC.",
                withDismissAction = true
            )
        }
    }
}

private fun aplicarBncc(plan: LessonPlan, resposta: BnccResposta): LessonPlan {
    val habilidades = resposta.habilidades.joinToString("\n") { h ->
        if (h.descricao.isBlank()) h.codigo else "${h.codigo} — ${h.descricao}"
    }
    val competencias = resposta.competencias.joinToString("\n") { c ->
        "Competência Geral ${c.numero}: ${c.descricao}"
    }
    val habilidadesTexto = listOfNotNull(
        habilidades.ifBlank { null },
        resposta.observacoes.ifBlank { null }?.let { "\nObservações: $it" }
    ).joinToString("\n").ifBlank { plan.habilidadesBncc }

    return plan.copy(
        habilidadesBncc = habilidadesTexto,
        competenciasGerais = competencias.ifBlank { plan.competenciasGerais }
    )
}
