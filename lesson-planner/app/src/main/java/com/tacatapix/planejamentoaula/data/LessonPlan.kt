package com.tacatapix.planejamentoaula.data

import kotlinx.serialization.Serializable

@Serializable
data class LessonPlan(
    val escola: String = "",
    val professor: String = "",
    val componenteCurricular: String = "",
    val anoSerie: String = "",
    val turma: String = "",
    val data: String = "",
    val duracao: String = "",
    val tema: String = "",
    val objetivos: String = "",
    val conteudos: String = "",
    val habilidadesBncc: String = "",
    val competenciasGerais: String = "",
    val metodologia: String = "",
    val recursos: String = "",
    val avaliacao: String = "",
    val referencias: String = ""
)

data class LessonPlanField(
    val label: String,
    val placeholder: String,
    val singleLine: Boolean = false,
    val getter: (LessonPlan) -> String,
    val setter: (LessonPlan, String) -> LessonPlan
)

val lessonPlanFields: List<LessonPlanField> = listOf(
    LessonPlanField(
        label = "Escola",
        placeholder = "Nome da escola",
        singleLine = true,
        getter = { it.escola },
        setter = { plan, v -> plan.copy(escola = v) }
    ),
    LessonPlanField(
        label = "Professor(a)",
        placeholder = "Nome do(a) professor(a)",
        singleLine = true,
        getter = { it.professor },
        setter = { plan, v -> plan.copy(professor = v) }
    ),
    LessonPlanField(
        label = "Componente Curricular",
        placeholder = "Ex.: Língua Portuguesa, Matemática, Ciências",
        singleLine = true,
        getter = { it.componenteCurricular },
        setter = { plan, v -> plan.copy(componenteCurricular = v) }
    ),
    LessonPlanField(
        label = "Ano/Série",
        placeholder = "Ex.: 5º ano do Ensino Fundamental",
        singleLine = true,
        getter = { it.anoSerie },
        setter = { plan, v -> plan.copy(anoSerie = v) }
    ),
    LessonPlanField(
        label = "Turma",
        placeholder = "Ex.: 5A",
        singleLine = true,
        getter = { it.turma },
        setter = { plan, v -> plan.copy(turma = v) }
    ),
    LessonPlanField(
        label = "Data",
        placeholder = "Ex.: 15/08/2025",
        singleLine = true,
        getter = { it.data },
        setter = { plan, v -> plan.copy(data = v) }
    ),
    LessonPlanField(
        label = "Duração",
        placeholder = "Ex.: 2 aulas de 50 minutos",
        singleLine = true,
        getter = { it.duracao },
        setter = { plan, v -> plan.copy(duracao = v) }
    ),
    LessonPlanField(
        label = "Tema da aula",
        placeholder = "Ex.: Interpretação de textos narrativos",
        singleLine = true,
        getter = { it.tema },
        setter = { plan, v -> plan.copy(tema = v) }
    ),
    LessonPlanField(
        label = "Objetivos de aprendizagem",
        placeholder = "O que os alunos devem aprender ao final da aula",
        getter = { it.objetivos },
        setter = { plan, v -> plan.copy(objetivos = v) }
    ),
    LessonPlanField(
        label = "Conteúdos",
        placeholder = "Conteúdos conceituais, procedimentais e atitudinais",
        getter = { it.conteudos },
        setter = { plan, v -> plan.copy(conteudos = v) }
    ),
    LessonPlanField(
        label = "Habilidades BNCC",
        placeholder = "Clique em \"Gerar BNCC\" para sugerir automaticamente",
        getter = { it.habilidadesBncc },
        setter = { plan, v -> plan.copy(habilidadesBncc = v) }
    ),
    LessonPlanField(
        label = "Competências gerais da BNCC",
        placeholder = "Competências gerais trabalhadas",
        getter = { it.competenciasGerais },
        setter = { plan, v -> plan.copy(competenciasGerais = v) }
    ),
    LessonPlanField(
        label = "Metodologia / Desenvolvimento",
        placeholder = "Descreva o passo a passo da aula",
        getter = { it.metodologia },
        setter = { plan, v -> plan.copy(metodologia = v) }
    ),
    LessonPlanField(
        label = "Recursos didáticos",
        placeholder = "Livro didático, quadro, datashow, materiais manipuláveis…",
        getter = { it.recursos },
        setter = { plan, v -> plan.copy(recursos = v) }
    ),
    LessonPlanField(
        label = "Avaliação",
        placeholder = "Como a aprendizagem será avaliada",
        getter = { it.avaliacao },
        setter = { plan, v -> plan.copy(avaliacao = v) }
    ),
    LessonPlanField(
        label = "Referências",
        placeholder = "Livros, artigos e sites consultados",
        getter = { it.referencias },
        setter = { plan, v -> plan.copy(referencias = v) }
    )
)
