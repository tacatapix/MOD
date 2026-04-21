package com.tacatapix.planejamentoaula.pdf

import android.content.Context
import android.content.Intent
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import androidx.core.content.FileProvider
import com.tacatapix.planejamentoaula.data.LessonPlan
import com.tacatapix.planejamentoaula.data.lessonPlanFields
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object PdfExporter {

    private const val PAGE_WIDTH = 595
    private const val PAGE_HEIGHT = 842
    private const val MARGIN = 40f
    private const val LINE_HEIGHT = 16f

    suspend fun exportarParaPdf(context: Context, plan: LessonPlan): File = withContext(Dispatchers.IO) {
        val document = PdfDocument()

        val titlePaint = Paint().apply {
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            textSize = 18f
            isAntiAlias = true
        }
        val labelPaint = Paint().apply {
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            textSize = 12f
            isAntiAlias = true
        }
        val bodyPaint = Paint().apply {
            typeface = Typeface.DEFAULT
            textSize = 11f
            isAntiAlias = true
        }

        var pageNumber = 1
        var pageInfo = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create()
        var page = document.startPage(pageInfo)
        var canvas = page.canvas
        var y = MARGIN + 20f

        canvas.drawText("Planejamento de Aula", MARGIN, y, titlePaint)
        y += 28f

        for (field in lessonPlanFields) {
            val value = field.getter(plan).trim()
            if (value.isEmpty()) continue

            val labelHeight = LINE_HEIGHT + 4f
            val lines = wrapText(value, bodyPaint, PAGE_WIDTH - 2 * MARGIN)
            val totalHeight = labelHeight + lines.size * LINE_HEIGHT + 8f

            if (y + totalHeight > PAGE_HEIGHT - MARGIN) {
                document.finishPage(page)
                pageNumber++
                pageInfo = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create()
                page = document.startPage(pageInfo)
                canvas = page.canvas
                y = MARGIN + 20f
            }

            canvas.drawText(field.label, MARGIN, y, labelPaint)
            y += labelHeight

            for (line in lines) {
                if (y + LINE_HEIGHT > PAGE_HEIGHT - MARGIN) {
                    document.finishPage(page)
                    pageNumber++
                    pageInfo = PdfDocument.PageInfo.Builder(PAGE_WIDTH, PAGE_HEIGHT, pageNumber).create()
                    page = document.startPage(pageInfo)
                    canvas = page.canvas
                    y = MARGIN + 20f
                }
                canvas.drawText(line, MARGIN, y, bodyPaint)
                y += LINE_HEIGHT
            }
            y += 8f
        }

        document.finishPage(page)

        val outDir = File(context.filesDir, "pdfs").apply { mkdirs() }
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val outFile = File(outDir, "planejamento_$stamp.pdf")
        FileOutputStream(outFile).use { document.writeTo(it) }
        document.close()

        outFile
    }

    fun compartilhar(context: Context, file: File) {
        val uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "application/pdf"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(
            Intent.createChooser(intent, "Compartilhar PDF")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    }

    private fun wrapText(text: String, paint: Paint, maxWidth: Float): List<String> {
        val result = mutableListOf<String>()
        val paragraphs = text.split("\n")
        for (paragraph in paragraphs) {
            if (paragraph.isBlank()) {
                result.add("")
                continue
            }
            val words = paragraph.split(" ")
            var current = StringBuilder()
            for (word in words) {
                val candidate = if (current.isEmpty()) word else "$current $word"
                if (paint.measureText(candidate) <= maxWidth) {
                    current = StringBuilder(candidate)
                } else {
                    if (current.isNotEmpty()) {
                        result.add(current.toString())
                    }
                    current = StringBuilder(word)
                }
            }
            if (current.isNotEmpty()) {
                result.add(current.toString())
            }
        }
        return result
    }
}
