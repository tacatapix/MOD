package com.tacatapix.planejamentoaula.ai

import com.tacatapix.planejamentoaula.data.LessonPlan
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class OpenAIClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    suspend fun gerarBncc(apiKey: String, plan: LessonPlan): Result<BnccResposta> = withContext(Dispatchers.IO) {
        if (apiKey.isBlank()) {
            return@withContext Result.failure(IllegalStateException("Configure a chave da API OpenAI em Ajustes."))
        }

        val prompt = construirPrompt(plan)

        val body = ChatRequest(
            model = "gpt-4o-mini",
            temperature = 0.2,
            responseFormat = ResponseFormat("json_object"),
            messages = listOf(
                Message(
                    role = "system",
                    content = """Você é um especialista em BNCC (Base Nacional Comum Curricular) do Brasil.
Sua tarefa é analisar um planejamento de aula e sugerir:
1) Habilidades BNCC aplicáveis (códigos oficiais como EF05LP01, EF67EF03, EM13CHS101, EI03TS01, etc.) com a descrição oficial resumida.
2) Competências gerais da BNCC (1 a 10) pertinentes.
3) Todos os textos devem estar em português do Brasil com ortografia correta.
Retorne SEMPRE um JSON válido com o formato:
{
  "habilidades": [ { "codigo": "EF05LP01", "descricao": "..." } ],
  "competencias": [ { "numero": 4, "descricao": "..." } ],
  "observacoes": "texto curto opcional"
}"""
                ),
                Message(role = "user", content = prompt)
            )
        )

        val requestBody = json.encodeToString(ChatRequest.serializer(), body)
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("https://api.openai.com/v1/chat/completions")
            .addHeader("Authorization", "Bearer $apiKey")
            .post(requestBody)
            .build()

        try {
            client.newCall(request).execute().use { response ->
                val raw = response.body?.string().orEmpty()
                if (!response.isSuccessful) {
                    return@withContext Result.failure(
                        RuntimeException("OpenAI HTTP ${response.code}: $raw")
                    )
                }
                val parsed = json.decodeFromString(ChatResponse.serializer(), raw)
                val content = parsed.choices.firstOrNull()?.message?.content.orEmpty()
                val bncc = json.decodeFromString(BnccResposta.serializer(), content)
                Result.success(bncc)
            }
        } catch (t: Throwable) {
            Result.failure(t)
        }
    }

    private fun construirPrompt(plan: LessonPlan): String = buildString {
        appendLine("Analise o planejamento de aula abaixo e sugira habilidades e competências da BNCC.")
        appendLine()
        appendLine("Componente curricular: ${plan.componenteCurricular.ifBlank { "(não informado)" }}")
        appendLine("Ano/Série: ${plan.anoSerie.ifBlank { "(não informado)" }}")
        appendLine("Tema da aula: ${plan.tema.ifBlank { "(não informado)" }}")
        if (plan.objetivos.isNotBlank()) {
            appendLine("Objetivos: ${plan.objetivos}")
        }
        if (plan.conteudos.isNotBlank()) {
            appendLine("Conteúdos: ${plan.conteudos}")
        }
        if (plan.metodologia.isNotBlank()) {
            appendLine("Metodologia: ${plan.metodologia}")
        }
    }
}

@Serializable
data class BnccResposta(
    val habilidades: List<Habilidade> = emptyList(),
    val competencias: List<Competencia> = emptyList(),
    val observacoes: String = ""
)

@Serializable
data class Habilidade(val codigo: String = "", val descricao: String = "")

@Serializable
data class Competencia(val numero: Int = 0, val descricao: String = "")

@Serializable
private data class ChatRequest(
    val model: String,
    val messages: List<Message>,
    val temperature: Double = 0.2,
    @SerialName("response_format") val responseFormat: ResponseFormat? = null
)

@Serializable
private data class ResponseFormat(val type: String)

@Serializable
private data class Message(val role: String, val content: String)

@Serializable
private data class ChatResponse(val choices: List<Choice> = emptyList())

@Serializable
private data class Choice(val message: Message)
