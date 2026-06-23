# KAG: Boosting LLMs in Professional Domains viaKnowledge Augmented Generation

Lei Liang∗,1, Mengshu $\boldsymbol { \mathrm { S u n } } ^ { * , 1 }$ , Zhengke Gui∗,1, Zhongshu $\mathrm { Z h u ^ { 1 } }$ , Ling Zhong1, Peilong Zhao1,Zhouyu Jiang1, Yuan $\mathrm { Q u } ^ { 1 }$ , Zhongpu ${ \mathbf B } { \mathbf o } ^ { 1 }$ , Jin Yang1, Huaidong Xiong1, Lin Yuan1, Jun ${ \mathrm { X u } } ^ { 1 }$ ,Zaoyang Wang1, Zhiqiang Zhang1, Wen Zhang2, Huajun Chen2, Wenguang Chen1, Jun Zhou†,1

{leywar.liang, mengshu.sms, zhengke.gzk, jun.zhoujun}@antgroup.com

1Ant Group Knowledge Graph Team, 2Zhejiang University

Github:https://github.com/OpenSPG/KAG

# Abstract

The recently developed retrieval-augmented generation (RAG) technology has en-abled the efficient construction of domain-specific applications. However, it alsohas limitations, including the gap between vector similarity and the relevance ofknowledge reasoning, as well as insensitivity to knowledge logic, such as numeri-cal values, temporal relations, expert rules, and others, which hinder the effective-ness of professional knowledge services. In this work, we introduce a professionaldomain knowledge service framework called Knowledge Augmented Generation(KAG). KAG is designed to address the aforementioned challenges with the mo-tivation of making full use of the advantages of knowledge graph(KG) and vectorretrieval, and to improve generation and reasoning performance by bidirection-ally enhancing large language models (LLMs) and KGs through five key aspects:(1) LLM-friendly knowledge representation, (2) mutual-indexing between knowl-edge graphs and original chunks, (3) logical-form-guided hybrid reasoning en-gine, (4) knowledge alignment with semantic reasoning, and (5) model capabilityenhancement for KAG. We compared KAG with existing RAG methods in multi-hop question answering and found that it significantly outperforms state-of-the-artmethods, achieving a relative improvement of $1 9 . 6 \%$ on hotpotQA and $3 3 . 5 \%$ on2wiki in terms of F1 score. We have successfully applied KAG to two profes-sional knowledge Q&A tasks of Ant Group, including E-Government Q&A andE-Health Q&A, achieving significant improvement in professionalism comparedto RAG methods. Furthermore, we will soon natively support KAG on the open-source KG engine OpenSPG, allowing developers to more easily build rigorousknowledge decision-making or convenient information retrieval services. Thiswill facilitate the localized development of KAG, enabling developers to builddomain knowledge services with higher accuracy and efficiency.

# 1 Introduction

Recently, the rapidly advancing Retrieval-Augmented Generation (RAG)[1, 2, 3, 4, 5] technologyhas been instrumental in equipping Large Language Models (LLMs) with the capability to acquire

domain-specific knowledge. This is achieved by leveraging external retrieval systems, thereby sig-nificantly reducing the occurrence of answer hallucinations and allows for the efficient constructionof applications in specific domains. In order to enhance the performance of the RAG system inmulti-hop and cross-paragraph tasks, knowledge graph, renowned for strong reasoning capabili-ties, have been introduced into the RAG technical framework, including GraphRAG[6], DALK[7],SUGRE[8], ToG 2.0[9], GRAG[10], GNN-RAG [11] and HippoRAG[12].

Although RAG and its optimization have solved most of the hallucination problems caused by a lackof domain-specific knowledge and real-time updated information, the generated text still lacks co-herence and logic, rendering it incapable of producing correct and valuable answers, particularly inspecialized domains such as law, medicine, and science where analytical reasoning is crucial. Thisshortcoming can be attributed to three primary reasons. Firstly, real-world business processes typi-cally necessitate inferential reasoning based on the specific relationships between pieces of knowl-edge to gather information pertinent to answering a question. RAG, however, commonly relies onthe similarity of text or vectors for retrieving reference information, which may lead to incompleteand repeated search results. secondly, real-world processes often involve logical or numerical rea-soning, such as determining whether a set of data increases or decreases in a time series, and thenext token prediction mechanism used by language models is still somewhat weak in handling suchproblems.

In contrast, the technical methodologies of knowledge graphs can be employed to address these is-sues. Firstly, KG organize information using explicit semantics; the fundamental knowledge unitsare SPO triples, comprising entities and the relationships between them[13]. Entities possess clearentity types, as well as relationships. Entities with the same meaning but expressed differently canbe unified through entity normalization, thereby reducing redundancy and enhancing the intercon-nectedness of knowledge [14]. During retrieval, the use of query syntax (such as SPARQL[15] andSQL[16]) enables the explicit specification of entity types, mitigating noisy from same named orsimilar entities, and allows for inferential knowledge retrieval by specifying relationships based onquery requirements, as opposed to aimlessly expanding into similar yet crucial neighboring content.Meanwhile, since the query results from knowledge graphs have explicit semantics, they can beused as variables with specific meanings. This enables further utilization of the LLM’s planning andfunction calling capabilities [17], where the retrieval results are substituted as variables into functionparameters to complete deterministic inferences such as numerical computations and set operations.

To address the above challenges and meet the requirements of professional domain knowledge ser-vices, we propose Knowledge Augmented Generation(KAG), which fully leverages the comple-mentary characteristics of KG and RAG techniques. More than merely integrating graph structuresinto the knowledge base process, it incorporates the semantic types and relationships of knowledgegraph and the commonly used Logical Forms from KGQA (Knowledge Graph Question Answer-ing) into the retrieval and generation process. As shown in Figure 1, this framework involves theoptimization of the following five modules:

• We proposed a LLM friendly knowledge representation framework LLMFriSPG. Werefer to the hierarchical structure of data, information, and knowledge of DIKW to upgradeSPG to be friendly to LLMs, named LLMFriSPG, to make it compatible with schema-free information extraction and schema-constrained expert knowledge construction on thesame knowledge type (such as entity type, event type), and supports the mutual-indexingrepresentation between graph structure and original text chunks, which facilitates the con-struction of graph-structure-based inverted index and facilitates the unified representation,reasoning, and retrieval of logical form.

• We proposed a logical-form-guided hybrid solving and reasoning engine. It includesthree types of operators: planning, reasoning and retrieval, transforming natural languagequestions into a problem-solving process that combines language and symbols. Each stepin the process can utilize different operators such as exact match retrieval, text retrieval,numerical computation, or semantic reasoning, thereby achieving the integration of fourdistinct problem-solving processes: retrieval, KG reasoning, language reasoning, and nu-merical computation.

• We proposed a knowledge alignment approach based on semantic reasoning. Definedomain knowledge as various semantic relations such as synonyms, hypernyms, and inclu-sions. Semantic reasoning is performed in both offline KG indexing and online retrieval

phases, allowing fragmented knowledge generated through automation to be aligned andconnected through domain knowledge. In the offline indexing phase, it can improve thestandardization and connectivity of knowledge, and in the online Q&A phase, it can serveas a bridge between user questions and indexing accurately.

• We proposed a model for KAG. To support the capabilities required for the operation ofthe KAG framework, such as index construction, retrieval, question understanding, seman-tic reasoning, and summarization, we enhance the three specific abilities of general LLMs:Natural Language Understanding (NLU), Natural Language Inference (NLI), and NaturalLanguage Generation (NLG) to achieve better performance in each functional module.

We evaluated the effectiveness of the system on three complex Q&A datasets:2WikiMultiHopQA[18], MuSiQue[19] and HotpotQA[20]. The evaluation focused on bothend-to-end Q&A performance and retrieval effectiveness. Experimental results showed thatcompared to HippoRAG[12], KAG achieved significant improvements across all three tasks, withF1 scores increasing by $1 9 . 6 \%$ , $12 . 2 \%$ and $12 . 5 \%$ respectively. Furthermore, retrieval metrics alsoshowed notable enhancements.

KAG is applied in two professional Q&A scenarios within Ant Group: E-Government and E-Health.In the E-Government scenario, it answers users’ questions about administrative processes based ona given repository of documents. For E-Health, it responds to inquiries related to diseases, symp-toms, treatments, utilizing the provided medical resources. Practical application results indicate thatKAG achieves significantly higher accuracy than traditional RAG methods, thereby enhancing thecredibility of Q&A applications in professional fields. We will soon natively support KAG on theopen source KG engine OpenSPG, allowing developers to more easily build rigorous knowledgedecision-making or convenient information retrieval services.

In summary, we propose a knowledge-augmented technical framework, KAG, targeting professionalquestion-answering scenarios and validate the effectiveness of this framework based on complexquestion-answering tasks. We present two industry application cases based on Ant Group’s businessscenarios and have open-sourced the code to assist developers in building local applications usingKAG.

# 2 Approach

In this section, we will first introduce the overall framework of KAG, and then discuss five keyenhancements in sections 2.1 to 2.5. As shown in Figure 1, the KAG framework consists of threeparts: KAG-Builder, KAG-Solver, and KAG-Model. The KAG-Builder is designed for buildingoffline indexes, in this module, we proposed a LLM Friendly Knowledge Representation frameworkand mutual-indexing between knowledge structure and text chunk. In the module KAG-Solver weintroduced a Logical-form-guided hybrid reasoning solver that integrates LLM reasoning, knowl-edge reasoning, and mathematical logic reasoning. Additionally, knowledge alignment by semanticreasoning is used to enhance the accuracy of knowledge representation and retrieval in both KAG-Builder and KAG-Solver. The KAG-Model optimizes the capabilities needed by each module basedon a general language model, thereby improving the performance of all modules.

# 2.1 LLM Friendly Knowledge Representation

In order to define a more friendly knowledge semantic representation for LLMs, we upgrade SPGfrom three aspects: deep text-context awareness, dynamic properties and knowledge stratification,and name it LLMFriSPG.

$$
\mathcal {M} = \{\mathcal {T}, \rho , \mathcal {C}, \mathcal {L} \}
$$

where, $\mathcal { M }$ represents all types defined in LLMFriSPG, $\mathcal { T }$ represents all EntityType(e.g., Person inFigure 2), EventType classes and all pre-defined properties that are compatible with LPG syntaxdeclarations. $\mathcal { C }$ represents all ConceptType classes, concepts and concept relations, it is worthnoting that the root node of each concept tree is a ConceptType class that is compatible with LPGsyntax(e.g., TaxoOfPerson in Figure 2.), each concept node has a unique ConceptType class. $\rho$represents the inductive relations from instances to conecepts. $\mathcal { L }$ represents all executable rulesdefined on logical relations and logical concepts. For $\forall t \in \mathcal T$ :

![](images/85e024d5240644e3bd645a02d7667b57be6bb2bffe301efc6354b18d7897900f.jpg)

Figure 1: The KAG Framework. The left side shows KAG-Builder, while the right side displaysKAG-Solver. The gray area at the bottom of the image represents KAG-Model.

![](images/7f19be600bb9763b49506da9e446338ba12923f7a3a2bced9a0155b6e8d74d7b.jpg)

Figure 2: LLMFriSPG:A knowledge representation framework that is friendly to LLMs. Instancesand concepts are separated to achieve more effective alignment with LLMs through concepts. In thisstudy, entity instances and event instances are collectively referred to as instances unless otherwisespecified. SPG properties are divided into knowledge and information areas, also called static anddynamic area, which are compatible with decision-making expertise with strong schema constraintsand document retrieval index knowledge with open information representation. The red dotted linerepresents the fusion and mining process from information to knowledge. The enhanced documentchunk representation provides traceable and interpretable text context for LLMs.

$$
p _ {t} = \left\{p _ {t} ^ {c}, p _ {t} ^ {f}, p _ {t} ^ {b} \right\}
$$

As is show in Figure 2, where, $p _ { t }$ represents all properties and relations of type $t$ , and $p _ { t } ^ { c }$ repre-sents the domain experts pre-defined part, $p _ { t } ^ { f }$ represents the part added in an ad-hoc manner, $p _ { t } ^ { b }$represents the system built-in properties, such as supporting_chunks, descripiton, summary and be-longTo. For any instance $e _ { i }$ , denote $t y p e o f ( e _ { i } )$ as $t _ { k }$ , and supporting_chunks represents the set of alltext chunks containing instance $e _ { i }$ , the user defines the chunk generation strategy and the maximumlength of the chunk in KAG builder phase, description represents the general descriptive informa-tion specific to class $t _ { k }$ . It is worth noting that the meaning of description added to the type $t _ { k }$ andthe instance $e _ { i }$ is different, when description is attached to $t _ { k }$ , it signifies the global description forthat type. Conversely, when it is associated with an instance $e _ { i }$ , it represents the general descriptiveinformation for $e _ { i }$ consistent with the orignal document context, description can effectively assistLLM in understanding the precise meaning of a specific instance or type, and can be used in taskssuch as information extraction, entity linking, and summary generation. summary represents thesummary of $e _ { i }$ or $r _ { j }$ in the original document context. belongTo represents the inductive semanticsfrom instance to concept. Each EntityType or EventType can be associated with a ConceptType

through belongTo. It is worth noting that, 1) $\mathcal { T }$ and $\mathcal { C }$ have different functions. The statementt adopts the object-oriented principle to better match the representation of the LPG[21], and $\mathcal { C }$ ismanaged by a text-based concept tree. This article will not introduce the SPG semantics in detail.2) $p _ { t } ^ { c }$ and $p _ { t } ^ { f }$ can be instantiated separately. That is, they share the same class declaration, but inthe instance storage space, pre-defined static properties and realtime-added dynamic properties cancoexist, and we also support instantiating only one of them. This approach can better balance theapplication scenarios of professional decision-making and information retrieval. General informa-tion retrieval scenarios mainly instantiate dynamic properties, while professional decision-makingapplication scenarios mainly instantiate static properties. Users can strike a balance between easeof use and professionalism based on business scenario requirements. 3) $p _ { t } ^ { c }$ and $p _ { t } ^ { f }$ share the sameconceptual terminology. Concepts are general common sense knowledge that is independent ofspecific documents or instances. Different instances are linked to the same concept node to achievethe purpose of classifying the instances. We can achieve semantic alignment between LLM and in-stances through concept graphs, and concepts can also be used as navigation for knowledge retrieval.the details are shown in section 2.4 and 2.3.

![](images/3c31592249480694703fd0bca9a2ccd8fbc9f15fd584b4e517999eaea40c3bb3.jpg)

Figure 3: Hierarchical representation of knowledge and information.

In order to more accurately define the hierarchical representation of information and knowledge,as shown in 3, we denote $K G _ { c s }$ as knowledge layer, which represents the domain knowledge thatcomplies with the domain schema constraints and has been summarized, integrated, and evaluated.denote $K G _ { f r }$ as graph information layer, which represents the graph data such as entities and re-lations obtained through information extraction. denote $R C$ as raw chunks layer, which representsthe original document chunks after semantic segmentation. the $K G _ { c s }$ layer fully complies with theSPG semantic specification and supports knowledge construction and logical rule definition withstrict schema constraints, SPG requires that domain knowledge must have pre-defined schema con-straints. It has high knowledge accuracy and logical rigor. However, due to its heavy reliance onmanual annotation, the labor cost of construction is relatively high and the information complete-ness is insufficient. $K G _ { f r }$ shares the same EntityTypes, Eventtypes and Conceptual system with$K G _ { c s }$ , and provides effective information supplement for $K G _ { c s }$ . Meanwhile, the supporting_chunks,summary, and description edges built between $K G _ { f r }$ and $R C$ form an inverted index based on graphstructure, making $R C$ an effective original-text-context supplement for $K G _ { f r }$ and with high infor-mation completeness. As is show in the right part of figure 3, in a specific domain application,$R ( K G _ { c s } )$ , $R \bar { ( } K G _ { f r } )$ , and $R ( R C )$ respectively represent their knowledge coverage in solving the tar-get domain problems. If the application has higher requirements for knowledge accuracy and logicrigorousness, it is necessary to build more domain structured knowledge and consume more expertmanpower to increase the coverage of $R ( K G _ { c s } )$ . On the contrary, if the application has higher re-quirements for retrieval efficiency and a certain degree of information loss or error tolerance, it isnecessary to increase the coverage of $R ( K G _ { f r } )$ to fully utilize KAG’s automated knowledge con-struction capabilities and reduce expert manpower consumption.

![](images/cc574760288b0109d59e6d2d19e5630715e1c00fe594c5d5f6fc777429461d30.jpg)

Figure 4: The Pipeline of KAG Builder for domain unstructured documents. From left to right, first,phrases and triples are obtained through information extraction, then disambiguation and fusion arecompleted through semantic alignment, and finally, the constructed KG is written into the storage.

# 2.2 Mutual Indexing

As illustrated in Figure 4, KAG-Builder consists of three coherent processes: structured informationacquisition, knowledge semantic alignment and graph storage writer. The main goals of this moduleinclude: 1) building a mutual-indexing between the graph structure and the text chunk to add moredescriptive context to the graph structure, 2) using the concept semantic graph to align differentknowledge granularities to reduce noise and increase graph connectivity.

# 2.2.1 Semantic Chunking

According to the document’s structural hierarchy and the inherent logical connections between para-graphs, a semantic chunking process is implemented based on system-built-in prompts. This seman-tic chunking produces chunks that adhere to both length constraints (specifically for LLM’s contextwindow size constraints) and semantic coherence, ensuring that the content within each chunk isthematically cohesive. We defined Chunk EntityType in RC, which includes fields such as id,summary, and mainText. Each chunk obtained after semantic segmentation will be written into aninstance of Chunk, where id is a composite field consisting of articleID, paraCode, idInPara con-catenated by the connector # in order to ensure that consecutive chunks are adjacent in the id space.articleID represents the globally unique article ID, paraCode represents the paragraph code in thearticle, and idInPara is the sequential code of each chunk in the paragraph. Consequently, an ad-jacency in the content corresponds to a sequential adjacency in their identifiers. Furthermore, areciprocal relation is established and maintained between the original document and its segmentedchunks, facilitating navigation and contextual understanding across different granularities of thedocument’s content. This structured approach to segmentation not only optimizes compatibilitywith large-scale language models but also preserves and enhances the document’s inherent semanticstructure and association.

# 2.2.2 Information Extraction with More Descriptive Context

Given a dataset, we use fine-tuning-free LLM(such as GPT-3.5, DeepSeek, QWen, etc,.) or ourfine-tuned model Hum to extract entities, events, concepts and relations to construct $K G _ { f r }$ , subse-quently, construct the mutual-indexing structure between $K G _ { f r }$ and $R C$ , enabling cross-documentlinks through entities and relations. This process includes three steps. First, it extracts the entityset $E = \{ e _ { 1 } , e _ { 2 } , e _ { 3 } , \ldots \}$ chunk by chunk, second, extracts the event set $E V = \left\{ e \nu _ { 1 } , e \nu _ { 2 } , e \nu _ { 3 } , . . . \right\}$ asso-ciated to all entities and iteratively extracts the relation set $R = \{ r _ { 1 } , r _ { 2 } , r _ { 3 } , \bar { . . . } \}$ between all entitiesin $E$ , finally, completes all hypernym relations between the instance and its spgClass. To providemore convenience for the subsequent Knowledge Alignment phase, and overcome the problem oflow discrimination of knowledge phrases such as Wikidata[22] and ConceptNet[23], in the entityextraction phase, we use LLMs to generate built-in properties description, summary, semanticType,spgClass, descripitonOfSemanticType by default for each instance $e$ at one time, as shown in Figure2, we store them in the $e$ instance storage according to the structure of e.description,e.summary, $< e$ ,belongTo, semanticType> and ${ < e _ { \mathrm { : } } }$ , hasClass, spgClass>.

![](images/032eb7300ae9ce8368664e19a19ee1a191083e669446d124060cb495ea548cd0.jpg)

Figure 5: An Example of KAG-Builder pipeline

# 2.2.3 Domain Knowledge Injection And Constraints

When openIE is applied to professional domains, irrelevant noise will be introduced. Previousresearches[3, 5, 24] have shown that noisy and irrelevant corpora can significantly undermine theperformance of LLMs. It is a challenge to align the granularity of extracted information and domainknowledge. The domain knowledge alignment capabilities in KAG include: 1) Domain term andconcept injection. We use an iterative extraction approach, First, we store domain concepts andterms with description in KG storage. Second, we extract all instances in the document throughopenIE, then we perform vector retrieval to obtain all possible concept and term sets $E _ { d }$ . Finally,we add $E _ { d }$ to the extraction prompt and perform another extraction to obtain a set $E _ { d } ^ { a }$ that is mostlyaligned with the domain knowledge. 2) Schema-constraint Extraction. In the vertical professionaldomains, the data structure between multiple documents in each data source such as drug instruc-tions, physical examination reports, government affairs, online order data, structured data tables,etc. has strong consistency, and is more suitable for information extraction with schema-constraint,structured Extraction also makes it easier to do knowledge management and quality improvement.For detailed information about knowledge construction based on Schema-constraint, please refer tothe $\mathrm { S P G ^ { 1 } }$ and OneKE[25]. This article will not introduce it in detail. It is worth noting that, asshown in figure 2, for the same entity type, such as Person, we can pre-define properties and rela-tions such as name, gender, placeOfBirth, (Person, hasFather, Person), (Person, hasFriend, Person),and can also extract tripples directly such as (Jay Chou, spgClass, Person), (Jay Chou, constellation,Capricorn), (Jay Chou, record company, Universal Music Group) through openIE. 3) Pre-definedKnowledge Structures By Document Type. Professional documents such as drug instructions,government affairs documents, and legal definitions generally have a relatively standardized docu-ment structure. Each type of document can be defined as an entity type, and different paragraphs aredifferent properties of the entity. Taking government affairs as an example, we can pre-define theGovernmentAffair EntityType and properites such as administrative divisions, service procedures,required materials, service locations, and target groups. The divided chunks are the values of dif-ferent properties. If the user asks "What materials are needed to apply for housing provident fund inXihu District?", you can directly take out the chunk corresponding to property required materials toanswer the question, avoiding the possible hallucinations caused by LLM re-generation.

# 2.2.4 Mutual indexing between text chunk vectors and knowledge structures

KAG’s mutual-indexing is a knowledge management and storage mechanism that conforms to theLLMFriSPG semantic representation. As is described in section 2.1, it includes four core datastructures: 1) Shared Schemas are coarse-grained-types pre-defined as SPG Classes at project level,it includes EntityTypes, ConceptTypes, and EventTypes, they serve as a high-level categorizationsuch as Person, Organization, GEOLocation, Date, Creature, Work, Event. 2) Instance Graphinclude all event and entity instances in $K G _ { c s }$ and $K G _ { f r }$ . that is, instances constructed through

openIE with schema-free or structured extraction with schema-constraint are both stored as instancesin KG storage. 3) Text Chunks are special entity node that conforms to the definition of the ChunkEntityType. 4) Concept Graph is the core component for knowledge alignment. it consists of aseries of concepts and concept relations, concept nodes are also fine-grained-types of instances.Through relation prediction, instance nodes can be linked to concept nodes to obtain their fine-grained semantic types. , and two storage structures: 1) KG Store. Store KG data structures inLPG databases, such as TuGraph, Neo4J. 2) Vector Store. Store text and vectors in a vector storageengine, such as ElasticSearch, Milvus, or the vector storage embedded in the LPG engine.

# 2.3 Logical Form Solver

In the process of solving complex problems, three key steps are involved: planning, reasoning andretrieval. Disassembling question is a planning process to determine the next problem to be tack-led. Reasoning includes retrieving information based on the disassembled question, inferring theanswer to the question according to the retrieved results, or re-disassembling the sub-question whenthe retrieved content cannot answer the question. Retrieval is to find the content that can be usedas reference for the original question or the disassembled sub-question. Since interactions between

Algorithm 1 Logical Form Solver

1: memory  $\leftarrow []$    
2: querycur  $\leftarrow$  query   
3: for round  $\in (0,n)$  do   
4:  $l f_{list}\gets$  LFPlanner(querycur)   
5: history  $\leftarrow []$    
6: for  $lf\in lflist$  do   
7:  $l f_{subquery},l f_{func}\gets l f$    
8: retrievalsub, answersub  $\leftarrow$  Reasoner(lfsubquery,lffunc)   
9: history.append([lfsubquery,retrievalsub,answersub])   
10: end for   
11: memory  $\leftarrow$  Memory(query, history)   
12: if not Judge(query, memory) then   
13: querycur  $\leftarrow$  SupplyQuery(query, memory)   
14: end if   
15: end for   
16: answer  $\leftarrow$  Generator(query, memory)   
17: return answer

different modules in traditional RAG are based on vector representations of natural language, in-accuracies often arise. Inspired by the logical forms commonly used in KGQA, we designed anexecutable language with reasoning and retrieval capabilities. This language breaks down a ques-tion into multiple logical expressions, each of which may include functions for retrieval or logicaloperations. The mutual indexing described in Section 2.2 makes this process possible. Meanwhile,we designed a multi-turn solving mechanism based on reflection and global memory, inspired byReSP[26]. The KAG solving process, as referenced in Figure 6 and Algorithm 17, first decom-poses the current question querycur into a list of subquestions $l f _ { l i s t }$ represented in logical form, andperforms hybrid reasoning to solve them. If an exact answer can be obtained through multi-hopreasoning over structured knowledge, it returns the answer directly. Otherwise, it reflects on thesolution results: storing the answers and retrieval results corresponding to $l f _ { l i s t }$ in global memoryand determining whether the question is resolved. If not, it generates supplementary questions andproceeds to the next iteration. Section 2.3.1, 2.3.2 and 2.3.3 introduce logical form function for plan-ning, logical form for reasoning and logical form for retrieval respectively. In general, the proposedlogical form language has the following three advantages:

• The use of symbolic language enhances the rigor and interpretability of problem decompo-sition and reasoning.

• Make full use of LLMFriSPG hierarchical representation to retrieve facts and texts knowl-edge guided by the symbolic graph structure

• Integrate the problem decomposition and retrieval processes to reduce the system complex-ity.

![](images/9863c6a9ce7a22541986a23f79bd9f5d2c67c9138171d688f7ed0e5a54b9837a.jpg)

Figure 6: An Example of logical form execution. In this figure, the construction process of KGon the left is shown in Figure 5, and the overall reasoning and iteration process is on the right.First, a logical form decomposition is performed based on the user’s overall question, and thenlogical-form-guided reasoning is used for retrieval and reasoning. Finally, Generation determineswhether the user’s question is satisfied. If not, a new question is supplied to enter a new logical formdecomposition and reasoning process. If it is determined to be satisfied, Generation directly outputsthe answer.

Table 13 illustrates a multi-round scenario consistent with pseudocode 17. Although first roundthe exact number of plague occurrences couldn’t be determined, but we can extracted informationindicates: "Venice, the birthplace of Antonio Vivaldi, experienced the devastating Black Death, alsoknown as the Great Plague. This pandemic caused by Yersinia pestis led to 75 to 200 milliondeaths in Eurasia, peaking in Europe from 1347 to 1351. The plague brought significant upheavalsin Europe. Although specific occurrence records in Venice aren’t detailed, it’s clear the city wasimpacted during the mid-14th century.". As is shown in Table 13,After two iterations, the answerdetermined is: 22 times.

# 2.3.1 Logical Form Planning

Logical Functions are defined as Table 1, with each function representing an execution action. Com-plex problems are decomposed by planning a combination of these expressions, enabling reasoningabout intricate issues.

<table><tr><td>Function Name</td><td>Function Declaration</td></tr><tr><td>Retrieval</td><td>Retrieval(s = si : type[name], p = pi : edge, o = oi : type[name],
s_prop = value, p_prop = value, o_prop = value)</td></tr><tr><td>Sort</td><td>Sort(A, direction = min|max, limit = n)</td></tr><tr><td>Math</td><td>mathi = Math(expr),
expr is in LaTeX syntax and can be used to perform operations on sets.
e.g. count: ||A||, sum: ΣA</td></tr><tr><td>Deduce</td><td>Deduce(left = A, right = B, op = entailment|greater|less|equal)</td></tr><tr><td>Output</td><td>Output(A, B, ...)</td></tr></table>

Table 1: Functions of logical form.

Retrieval. According to the the knowledge or information retrieved from SPO, s, p, o should notrepeatedly appear multiple times in the same expression. Constraints can be applied to the s, p, o for

querying. For multi-hop queries, multiple retrievals are required. When the current variable refers toa previously mentioned variable, the variable name must be consistent with the referenced variablename, and only the variable name needs to be provided. The knowledge type and name are onlyspecified during the first reference.

Sort. Sort the retrieved results. A is the variable name for the retrieved subject-predicate-object(SPO) $( s _ { i } , ~ o _ { i }$ , or s.prop, p.prop, o.prop). direction specifies the sorting direction, wheredirection $=$ min means sorting in ascending order and direction $=$ max means sorting in descendingorder. limit $= n$ indicates outputting the topN results.

Math. Perform mathematical calculations. expr is in LaTeX syntax and can be used to performcalculations on the retrieved results (sets) or constants. mat $h _ { i }$ represents the result of the calculationand can be used as a variable name for reference in subsequent actions.

Deduce. Deduce the retrieval or calculation results to answer the question. $A , B$ can be the vari-able names from the retrieved SPO or constants. The operator $o p =$ entailment|greater|less|equalrepresents $A$ entails $B , A$ is greater than $B , A$ is less than $B$ , and A is equal to $B$ , respectively.

# 2.3.2 Logical Form for Reasoning

When the query statement represented by natural language is applied to the search, the logic is oftenfuzzy, such as "find a picture containing vegetables or fruits" and "find a picture containing veg-etables and fruits". Whether text search or vector search is used, the similarity between the twoqueries is very high, but the corresponding answers are quite different. The same is true for prob-lems involving logical reasoning processes such as and or not, and intersection differences. To thisend, we use logical form to express the question, so that it can express explicit semantic relations.Similar to IRCOT, we decompose complex original problem and plan out various execution actionssuch as multi-step retrieval, numerical reasoning, logical reasoning, and semantic deduce. Eachsub-problem is expressed using logical form functions, and dependencies between sub-questionsare established through variable references. The inference resolution process for each sub-questionis illustrated as Algorithm 9. In this process, the GraphRetrieval module performs KG structureretrieval according to the logical form clause to obtain structured graph results. Another key mod-ule, HybridRetrieval, combining natural language expressed sub-problems and logical functionsfor comprehensive retrieval of documents and sub-graph information. To understand how logicalfunctions can be utilized to reason about complex problems, refer to the following examples asTable 14.

Output. Directly output $A , B , \ldots$ as the answers. Both $A$ and $B$ are variable names that reference thepreviously retrieved or calculated

# Algorithm 2 Logical Form Reasoner

Require: Each sub-query resulting from the decomposition of a question based on the logical form,along with their respective logical function, are denoted as $l f _ { s u b q u e r y }$ and l f f unc

Ensure: The retrievals and answer of each sub-query, are denoted as $r e t r i _ { s u b }$ and answersubret $r i _ { k g } \gets$ GraphRetrieval(l fsubquery, l f f unc)

2: if retrikg ̸= None and ret $r i _ { k g } >$ threshold then$r e t r i _ { s u b } \gets r e t r i _ { k g }$

4: elseretridoc ← HybridRetrieval(l fsubquery, retrikg)

6: retrisub ← retrikg, retridocend if

8: answersub ← Generator(l fsubquery, retrisub)return retrisub, answersub

# 2.3.3 Logical Form for Retrieval

In naive RAG, retrieval is achieved by calculating the similarity (e.g. cosine similarity) between theembeddings of the question and document chunks, where the semantic representation capability ofembedding models plays a key role. This mainly includes a sparse encoder (BM25) and a dense re-triever (BERT architecture pre-training language models). Sparse and dense embedding approaches

capture different relevance features and can benefit from each other by leveraging complementaryrelevance information.

The existing method of combining the two is generally to combine the scores of the two searchmethods in an ensemble, but in practice different search methods may be suitable for different ques-tions, especially in questions requiring multi-hop reasoning. When query involves proper nouns,people, places, times, numbers, and coordinates, the representation ability of the pre-trained presen-tation model is limited, and more accurate text indexes are needed. For queries that are closer to theexpression of a paragraph of text, such as scenes, behaviors, and abstract concepts, the two may becoupled in some questions.

In the design of logical form, it is feasible to effectively combine two retrieval methods. Whenkeyword information is needed as explicit filtering criteria, conditions for selection can be specifiedwithin the retrieval function to achieve structured retrieval.

For example, for the query "What documents are required to apply for a disability cer-tificate at West Lake, Hangzhou?", the retrieval function could be represented as: "Re-trieval(s=s1:Event[applying for a disability certificate], p=p1:support_chunks, o=o1:Chunk,s.location $=$ West Lake, Hangzhou)". This approach leverages the establishment of different indices(sparse or dense) to facilitate precise searches or fuzzy searches as needed.

Furthermore, when structured knowledge in the form of SPO cannot be retrieved using logicalfunctions, alternative approaches can be employed. These include semi-structured retrieval, whichinvolves using logical functions to search through chunks of information, and unstructured re-trieval. The latter encompasses methods such as Retrieval-Augmented Generation (RAG), wheresub-problems expressed in natural language are used to retrieve relevant chunks of text. This high-lights the adaptability of the system to leverage different retrieval strategies based on the availabilityand nature of the information.

# 2.4 Knowledge Alignment

Constructing KG index through information-extraction and retrieving based on vector-similarity hasthree significant defects in knowledge alignment:

• Misaligned semantic relations between knowledge. Specific semantic relations, suchas contains, causes and isA, are often required between the correct answer and the query,while the similarity relied upon in the retrieval process is a weak semantic measure thatlacks properties and direction, which may lead to imprecise retrieval of content.

• Misaligned knowledge granularity. The problems of knowledge granularity difference,noise, and irrelevance brought by openIE pose great challenges to knowledge management.Due to the diversity of language expressions, there are numerous synonymous or similarnodes, resulting in low connectivity between knowledge elements, making the retrievalrecall incomplete.

• Misaligned with the domain knowledge structure. There is a lack of organized, system-atic knowledge within specific domains. Knowledge that should be interrelated appears ina fragmented state, leading to a lack of professionalism in the retrieved content.

To solve these problems, we propose a solution that leverages concept graphs to enhance offlineindexing and online retrieval through semantic reasoning. This involves tasks such as knowledgeinstance standardization, instance-to-concept linking, semantic relation completion, and domainknowledge injection. As described in section 2.2.2, we added descriptive text information to eachinstance, concept or relation in the extraction phase to enhance its interpretability and contextual rel-evance. Meanwhile, as described in section 2.2.3, KAG supports the injection of domain conceptsand terminology knowledge to reduce the noise problem caused by the mismatch of knowledge gran-ularity in vertical domains. The goal of concept reasoning is to make full use of vector retrieval andconcept reasoning to complete concept relations based on the aforementioned knowledge structureto enhance the accuracy and connectivity of the domain KG. Refer to the definition of SPG conceptsemantics2, as is shown in Table 2, we have summarized six semantic relations commonly required

for retrieval and reasoning. Additional semantic relations can be added based on the specific re-quirements of the actual scenario.

<table><tr><td>Formal Expression</td><td>Description</td><td>Example</td></tr><tr><td>&lt;var1, synonym, var2&gt;</td><td>A synonym relation means that a word or phrase var2 that has the same or nearly the same meaning as another word or phrase var1 in the same language and given context.</td><td>Fast is a synonym of quick.</td></tr><tr><td>&lt;var1, isA, var2&gt;</td><td>An isA relation means that a hypernym var2 that is more generic or abstract than a given word or phrase var1 and encompasses a broader category that the given word belongs to.</td><td>Car isA Vehicle.</td></tr><tr><td>&lt;var1, isPartOf, var2&gt;</td><td>An isPartOf relation means that something var1 is a component or constituent of something var2 larger. This relation shows that an item is a part of a bigger whole.</td><td>Wheel isPartOf car.</td></tr><tr><td>&lt;var1, contains, var2&gt;</td><td>A contains relation means that something var1 includes or holds var2, something else within it. This indicates that one item has the other as a subset or component.</td><td>Library contains books.</td></tr><tr><td>&lt;var1, belongTo, var2&gt;</td><td>An belongTo relation means that something var1 is an instance of concept var2.</td><td>Chamber belongTo Legislative Body.</td></tr><tr><td>&lt;var1, causes, var2&gt;</td><td>A causes relation means that one event or action var1 brings about another var2. This indicates a causal relation where one thing directly results in the occurrence of another.</td><td>Fire causes smoke.</td></tr></table>

Table 2: Commonly used semantic relations.

# 2.4.1 Enhance Indexing

The process of enhancing indexing through semantic reasoning, as shown in Figure 5 , specificallyimplemented as predicting semantic relations or related knowledge elements among index itemsusing LLM, encompassing four strategies:

• Disambiguation and fusion of knowledge instances. Taking entity instance $e _ { c u r }$ as an ex-ample, first, the one-hop relations and description information of $e _ { c u r }$ are used to predictsynonymous relations to obtain the synonym instance set $E _ { s y n }$ of $e _ { c u r }$ . Then, the fused tar-get entity $e _ { t a r }$ is determined from $E _ { s y n }$ . Finally, the entity fusion rules are used to copy theproperties and relations of the remaining instances in $E _ { s y n }$ to $e _ { t a r }$ , and the names of theseinstances are added to the synonyms of $e _ { t a r }$ , the remaining instances will also be deletedimmediately.

• Predict relations between instances and concepts. For each knowledge instance (suchas event, entity), predict its corresponding concept and add the derived triple $<$$e _ { i }$ , belongTo, $c _ { j } >$ to the knowledge index. As is shown in Figure 5, <Chamber, belongTo,Legislative Body> means that the Chamber belongs to Legislative Body in classification.

• Complete concepts and relations between concepts. During the extraction process, we useconcept reasoning to complete all hypernym and isA relations between semanticType andspgClass. As is shown in Figure 5 and Table 2, we can obtain the semanticType of Cham-ber is Legislative Body, and its spgClass is Organization in the extraction phase. Throughsemantic completion, we can get <Legislative Body, isA, Government Agency>, <Govern-ment Agency, isA, Organization>. Through semantic completion, the triple information of$K G _ { f r }$ space is more complete and the connectivity of nodes is stronger.

# 2.4.2 Enhance Retrieval

In the retrieval phase, we utilize semantic relation reasoning to search the KG index based on thephrases and types in the logical form. For the types, mentions or relations in the logical form, we

employ the method of combining semantic relation reasoning with similarity retrieval to replace thetraditional similarity retrieval method. This retrieval method makes the retrieval path professionaland logical, so as to obtain the correct answer. First, the hybrid reasoning performs precise typematching and entity linking. If the type matching fails, then, semantic reasoning is performed. Asshown in Figure 6, if the type Political Party fails to match, semantic reasoning is used to predictthat Political Party contains Political Faction, and reasoning or path calculation is performedstarting from Political Faction.

Take another example. If the user query $q _ { 1 }$ is "Which public places can cataract patients gofor leisure?" and the document content $d _ { 2 }$ is "The museum is equipped with facilities to providebarrier-free visiting experience services such as touch, voice interpretation, and fully automaticguided tours for the visually impaired.", It is almost impossible to retrieve $d _ { 2 }$ based on the vectorsimilarity with $q _ { 1 }$ . However, it is easier to retrieve $d _ { 2 }$ through the semantic relation of <cataractpatient, isA, visually impaired>.

# 2.5 KAG-Model

KAG includes two main computational processes: offline index building and online query and an-swer generation. In the era of small language models, these two tasks were typically handled bytwo separate pipelines, each containing multiple task-specific NLP models. This results in highcomplexity for the application system, increased setup costs, and inevitable cascading losses due toerror propagation between modules. In contrast, large language models, as a capability complex,can potentially integrate these pipelines into a unified, simultaneous end-to-end reasoning process.

As shown in Figure 7, the processes of indexing and QA each consist of similar steps. Both of thetwo pipelines can be abstracted as classify, mention detection, mention relation detection, seman-tic alignment, embedding, and chunk, instance, or query-focused summary. Among these, classify,mention detection, and mention relation detection can be categorized as NLU, while semantic align-ment and embedding can be grouped under NLI. Finally, the chunk, instance or query-focused sum-mary can be classified under NLG. Thus, we can conclude that the three fundamental capabilities ofnatural language processing that a RAG system relies on are NLU, NLI, and NLG.

We focused on exploring methods to optimize these three capabilities, which are introduced in sub-sections 2.5.1, 2.5.2, and 2.5.3 respectively. Additionally, to reduce the cascade loss caused bylinking models into a pipeline, we further explored methods to integrate multiple inference pro-cesses into a single inference. Subsection 2.5.4 will discuss how to equip the model with retrievalcapabilities to achieve better performance and efficiency through one-pass inference.

![](images/c1e37b0ffad071e4e361c3a2ce422e2a4cf4d1fd85aeaebf88413d4e6be6c060.jpg)

Figure 7: The model capabilities required for KAG.

# 2.5.1 Natural Language Understanding

NLU is one of the most common foundational tasks in natural language processing, including textclassification, named entity recognition, relation Extraction, subject and object extraction, triggerdetection, event argument extraction, event extraction, and machine reading comprehension. Wehave collected over 30 public datasets to enhance understanding capabilities. Experiments foundthat simply transforming the original datasets into instruction datasets can achieve comparable re-sults to specialized models on trained tasks, but this approach does not improve the model’s NLUcapabilities on unseen domains. Therefore, we conducted large-scale instruction reconstruction, de-signing various instruction synthesis strategies to create an NLU instruction dataset with over 20,000diverse instructions. By utilizing this dataset for supervised fine-tuning on a given base model, themodel has demonstrated enhanced NLU capabilities in downstream tasks. The instruction recon-struction strategy mainly consists of the following three types.

• Label bucketing: [25]This strategy focuses on label-guided tasks, where the aim is to ex-tract text based on labels or map text to specified labels, including classification, NER, RE,and EE. When labels in a dataset collectively co-occur in the training set, the model maylearn this pattern and overfit to the dataset, failing to independently understand the mean-ing of each label. Therefore, during the instruction synthesis process, we adopt a pollingstrategy that designates only one label from each training sample as part of a bucket. Ad-ditionally, since some labels have similar semantics and can be confused, we group easilyconfused labels into a single bucket, allowing the model to learn the semantic differencesbetween the two labels more effectively.

• Flexible and Diverse Input and Output Formats: The LLM employs an instruction-following approach for inference, and a highly consistent input-output format may causethe model to overfit to specific tasks, resulting in a lack of generalization for unseen for-mats. Therefore, we have flexibly processed the input and output formats. The output ishandled as five different formatting instructions, as well as two types of natural languageinstructions. Additionally, the output format can dynamically be specified as markdown,JSON, natural language, or any format indicated in the examples.

• Instructoin with Task Guildline: Traditional NLP training often employs a "sea of ques-tions" approach, incorporating a wide variety of data in the training set. This allows themodel to understand task requirements during the learning process, such as whether to in-clude job titles when extracting personal names. For the training of LLMs, we aim for themodel to perform tasks like a professional annotator by comprehending the task descrip-tion. Therefore, for the collected NLU tasks, we summarize the task descriptions usinga process of self-reflection within the LLM. This creates training data that includes taskdescriptions within the instructions. Additionally, to enhance task diversity, we implementheuristic strategies to rephrase the task descriptions and answers. This enables the modelto understand the differences between task descriptions more accurately and to completetasks according to the instructions.

We fine-tuned six foundational models: qwen2, llama2, baichuan2, llama3, mistral, phi3, and usedsix understanding benchmarks recorded on OpenCompass for performance validation. The table 3shows that the KAG-Model has a significant improvement in NLU tasks.

# 2.5.2 Natural Language Inference

The NLI task is used to infer the semantic relations between given phrases. Typical NLI tasksinclude entity linking, entity disambiguation, taxonomy expansion, hypernym discovery, and textentailment. In the context of knowledge base Q&A, due to the diversity and ambiguity of naturallanguage expressions, as well as the subtle and different types of semantic connections betweenphrases, it often requires further alignment or retrieval of related information through NLI tasksbased on NLU. As described in section 2.4, we categorize the key semantic relation in knowledgebase applications into six types. Among these, relations such as isA, isPartOf and contains exhibitdirectional and distance-based partial order relations. During the reasoning process, it is crucial toaccurately determine these semantic relations to advance towards the target answer. In traditionalapproaches, separate training of representation pre-training models and KG completion(KGC) mod-els is often employed to reason about semantic relations. However, these KGC models tend to focus

<table><tr><td>Models</td><td>C3</td><td>WSC</td><td>XSum</td><td>Lambda</td><td>Lcsts</td><td>Race</td><td>Average</td></tr><tr><td>GPT4</td><td>95.10</td><td>74.00</td><td>20.10</td><td>65.50</td><td>12.30</td><td>92.35</td><td>59.89</td></tr><tr><td>Qwen2</td><td>92.27</td><td>66.35</td><td>18.68</td><td>62.39</td><td>13.07</td><td>88.37</td><td>56.86</td></tr><tr><td>KAGQwen2</td><td>92.88</td><td>70.19</td><td>31.33</td><td>66.16</td><td>18.53</td><td>88.17</td><td>61.21</td></tr><tr><td>Llama2</td><td>81.70</td><td>50.96</td><td>23.29</td><td>63.26</td><td>15.99</td><td>55.64</td><td>48.47</td></tr><tr><td>KAGLlama2</td><td>82.36</td><td>63.46</td><td>24.51</td><td>65.22</td><td>17.51</td><td>68.48</td><td>53.59</td></tr><tr><td>Baichuan2</td><td>84.44</td><td>66.35</td><td>20.81</td><td>62.43</td><td>16.54</td><td>76.85</td><td>54.57</td></tr><tr><td>KAGBaichuan2</td><td>84.11</td><td>66.35</td><td>21.51</td><td>62.64</td><td>17.27</td><td>77.18</td><td>54.84</td></tr><tr><td>Llama3</td><td>86.63</td><td>65.38</td><td>25.84</td><td>36.72</td><td>0.09</td><td>83.76</td><td>49.74</td></tr><tr><td>KAGLlama3</td><td>83.40</td><td>62.50</td><td>26.72</td><td>54.07</td><td>18.45</td><td>81.16</td><td>54.38</td></tr><tr><td>Mistral</td><td>67.29</td><td>30.77</td><td>21.16</td><td>59.98</td><td>0.78</td><td>73.46</td><td>42.24</td></tr><tr><td>KAGMistral</td><td>47.29</td><td>39.42</td><td>21.54</td><td>69.09</td><td>17.14</td><td>72.42</td><td>44.48</td></tr><tr><td>Phi3</td><td>68.60</td><td>42.31</td><td>0.60</td><td>71.74</td><td>3.47</td><td>73.18</td><td>43.32</td></tr><tr><td>KAGPhi3</td><td>85.21</td><td>25.94</td><td>0.36</td><td>71.24</td><td>15.49</td><td>74.00</td><td>45.37</td></tr></table>

Table 3: Enhancement of natural language understanding capabilities in different LLMs by KAG.The experimental results are based on the open-compass framework and tested using the “gen”mode. The evaluation metrics for C3, WSC, Lambda, and Race are ACC. XSum and Lcsts aremeasured using ROUGE-1. Race includes Race-middle and Race-high, and their average is taken.

on learning graph structures and do not fully utilize the essential textual semantic information forsemantic graph reasoning. LLMs possess richer intrinsic knowledge, and can leverage both seman-tic and structural information to achieve more precise reasoning outcomes. To this end, we havecollected a high-quality conceptual knowledge base and ontologies from various domains, creatinga conceptual knowledge set that includes 8,000 concepts and their semantic relations. Based onthis knowledge set, we constructed a training dataset that includes six different types of conceptualreasoning instructions to enhance the semantic reasoning capabilities of a given base model, therebyproviding semantic reasoning support for KAG.

Semantic reasoning is one of the core ability required in KAG process, we use NLI tasks and generalreasoning Q&A tasks to evaluate the ability of our model, the results are as shown in Table 4 andTable 5. The evaluation results indicates that our KAG-Model demonstrates a significant improve-ment in tasks related with semantic reasoning: First, Table 5 shows that on the Hypernym Discoverytask(which is consistent in form with the reasoning required in semantic enhanced indexing and re-trieval.), our fine-tuned KAG-llama model outperforms Llama3 and ChatGPT-3.5 significantly. Inaddition, the better performance of our model on CMNLI, OCNLI and SIQA compared with Llama3in Table 4 shows that our model has good capabilities in general logical reasoning.

<table><tr><td>Models</td><td>CMNLI</td><td>OCNLI</td><td>SIQA</td></tr><tr><td>Llama3</td><td>35.14</td><td>32.1</td><td>44.27</td></tr><tr><td>KAG-Llama3</td><td>49.52</td><td>44.31</td><td>65.81</td></tr></table>

Table 4: Enhancement of natural language Inference capabilities in different LLMs by KAG. Theevaluation metrics for CMNLI, OCNLI, SIQA are measured with accuracy.

<table><tr><td></td><td>1A.English</td><td>2A.Medical</td><td>2B.Music</td></tr><tr><td>ChatGPT-3.5</td><td>30.04</td><td>26.12</td><td>28.47</td></tr><tr><td>Llama3-8B</td><td>23.47</td><td>24.26</td><td>18.73</td></tr><tr><td>KAG-Llama3</td><td>38.26</td><td>55.14</td><td>30.16</td></tr></table>

Table 5: Hypernym Discovery performance comparison on SemEval2018-Task9 dataset, measuredin MRR.

# 2.5.3 Natural Language Generation

Models that have not undergone domain adaptation training often exhibit significant differencesfrom the target text in domain logic and writing style. Moreover, acquiring sufficient amounts ofannotated data in specialized domains frequently poses a challenge. Therefore, we have established

two efficient fine-tuning methods for specific domain scenarios, allowing the generation process tobetter align with scene expectations: namely, K-Lora and AKGF.

Pre-learning with K-LoRA. First of all, we think that using knowledge to generate answers is thereverse process of extracting knowledge from text. Therefore, by inverting the previously describedextraction process, we can create a ’triples-to-text’ generation task. With extensive fine-tuning on amultitude of instances, the model can be trained to recognize the information format infused by theKG. Additionally, as the target text is domain-specific, the model can acquire the unique linguisticstyle of that domain. Furthermore, considering efficiency, we continue to utilize LoRA-based SFT.We refer to the LoRA obtained in this step as K-LoRA.

Alignment with KG Feedback. The model may still exhibit hallucinations in its responses due toissues such as overfitting. Inspired by the RLHF(Reinforcement Learning with Human Feedback)approach[27, 28], we hope that the KG can serve as an automated evaluator, providing feedback onknowledge correctness of the current response, thereby guiding the model towards further optimiza-tion. First, we generate a variety of responses for each query by employing diverse input formats orrandom seeds. Subsequently, we incorporate the KG to score and rank these responses. The scoringprocess compare generated answer with knowledge in KG to ascertain their correctness. The rewardis determined by the number of correctly matched knowledge triples. The formula for calculatingthe reward is represented by Formula 1.

$$
r e w a r d = \log (r s p o + \alpha \times r e) \tag {1}
$$

where $\alpha$ is a hyperparameter, rspo represents the number of SPO matches, and re represents thenumber of entity matches.

We select two biomedical question-answering datasets, CMedQA[29] and BioASQ[30], for evalu-ating our model. CMedQA is a comprehensive dataset of Chinese medical questions and answers,while BioASQ is an English biomedical dataset. We randomly choose 1,000 instances from eachfor testing. For CMedQA, we employ the answer texts from the non-selected Q&A pairs as corporato construct a KG in a weakly supervised manner. Similarly, with BioASQ, we use all the pro-vided reference passages as the domain-specific corpora. Experimental results, as shown in Table6, demonstrate significant enhancement in generation performance. For more details on the specificimplementation process, please refer to our paper[31]

<table><tr><td rowspan="2">Model</td><td colspan="2">CMedQA</td><td colspan="2">BioASQ</td></tr><tr><td>Rouge-L</td><td>BLEU</td><td>Rouge-L</td><td>BLEU</td></tr><tr><td>ChatGPT-3.5 0-shot</td><td>14.20</td><td>1.78</td><td>21.14</td><td>5.93</td></tr><tr><td>ChatGPT-3.5 2-shot</td><td>14.66</td><td>2.53</td><td>21.42</td><td>6.11</td></tr><tr><td>Llama2</td><td>14.02</td><td>2.86</td><td>23.47</td><td>7.11</td></tr><tr><td>KAGLlama2</td><td>15.44</td><td>3.46</td><td>24.21</td><td>7.79</td></tr></table>

Table 6: Performance comparison on CMedQA & BioASQ. "CP" indicates "continual pre-trained".We consider continual pre-training as a basic method of domain knowledge infusion, on par withother retrieval-based methods. Consequently, we do not report on the outcomes of hybrid ap-proaches.

# 2.5.4 Onepass Inference

Most retrieval enhanced systems operate in a series of presentation models, retrievers, and gener-ation models, resulting in high system complexity, construction costs, and the inevitable concate-nation loss caused by error transfer between modules. We introduces an efficient one-pass unifiedgeneration and retrieval (OneGen) model to enable an arbitrary LLM to generate and retrieve inone single forward pass. Inspired by the latest success in LLM for text embedding, we expand theoriginal vocabulary by adding special tokens (i.e. retrieval tokens), and allocate the retrieval taskto retrieval tokens generated in an autoregressive manner. During training, retrieval tokens onlyparticipate in representation fine-tuning through contrastive learning, whereas other output tokensare trained using language model objectives. At inference time, we use retrieval tokens for efficientretrieving on demand. Unlike the previous pipeline approach where at least two models are neededfor retrieval and generation, OneGen unified them in one model, thus eliminating the need for aseparate retriever and greatly reducing system complexity.

As shown in experiment results in Table 7, we draw the following conclusions: (1) OneGen demon-strates efficacy in $R \to G$ task, and joint training of retrieval and generation yields performance gainson the RAG task. The Self-RAG endows LLMs with self-assessment and adaptive retrieval, whileOneGen adds self-retrieval. Our method outperforms the original Self-RAG across all datasets,especially achieving improvements of 3.1pt on Pub dataset and 2.8pt on ARC dataset, validatingthe benefits of joint training. (2) OneGen is highly efficient in training, with instruction-finetunedLLMs showing strong retrieval capabilities with minimal additional tuning. It requires less andlower-quality retrieval data, achieving comparable performance with just 60K noisy samples andincomplete documents, without synthetic data. For more details on the specific implementationprocess, please refer to paper[32]

<table><tr><td rowspan="3">BackBone</td><td rowspan="3">Retriever</td><td colspan="4">Generation Performance</td><td colspan="2">Retrieval Performance</td></tr><tr><td colspan="2">HotpotQA</td><td colspan="2">2WikiMultiHopQA</td><td>HotpotQA</td><td>2WikiMultiHopQA</td></tr><tr><td>EM</td><td>F1</td><td>EM</td><td>F1</td><td>Recall@1</td><td>Recall@1</td></tr><tr><td rowspan="2">Llama2-7B</td><td>Contriever</td><td>52.83</td><td>65.64</td><td>70.02</td><td>74.35</td><td>73.76</td><td>68.75</td></tr><tr><td>self</td><td>54.82</td><td>67.93</td><td>75.02</td><td>78.86</td><td>75.90</td><td>69.79</td></tr><tr><td rowspan="2">Llama3.1-7B</td><td>Contriever</td><td>53.72</td><td>66.46</td><td>70.92</td><td>75.29</td><td>69.79</td><td>66.80</td></tr><tr><td>self</td><td>55.38</td><td>68.35</td><td>75.88</td><td>79.60</td><td>72.55</td><td>68.98</td></tr><tr><td rowspan="2">Qwen2-1.5B</td><td>Contriever</td><td>48.55</td><td>61.02</td><td>68.32</td><td>72.66</td><td>72.41</td><td>67.70</td></tr><tr><td>self</td><td>48.75</td><td>60.98</td><td>73.84</td><td>77.44</td><td>72.70</td><td>69.27</td></tr><tr><td rowspan="2">Qwen2-7B</td><td>Contriever</td><td>53.32</td><td>66.22</td><td>70.80</td><td>74.86</td><td>74.15</td><td>69.01</td></tr><tr><td>self</td><td>55.12</td><td>67.60</td><td>76.17</td><td>79.82</td><td>75.68</td><td>69.96</td></tr></table>

Table 7: In RAG for Multi-Hop QA settings, performance comparison across different datasets usingdifferent LLMs.

# 3 Experiments

# 3.1 Experimental Settings

Datasets. To evaluate the effectiveness of the KAG for knowledge-intensive question-answeringtask, we perform experiments on 3 widely-used multi-hop QA datasets, including HotpotQA [20],2WikiMultiHopQA [18], and MuSiQue [19]. For a fair comparison, we follow IRCoT [33] andHippoRAG [12] utilizing 1,000 questions from each validation set and using the retrieval corpusrelated to selected questions.

Evaluation Metric. When evaluating QA performance, we use two metrics: Exact Match (EM)and F1 scores. For assessing retrieval performance, we calculate the hit rates based on the Top 2/5retrieval results, represented as Recall $\textcircled{2} 2$ and Recall $\textcircled { a } 5$ .

Comparison Methods. We evaluate our approach against several robust and commonly utilizedretrieval RAG methods. NativeRAG using ColBERTv2 [34] as retriever and directly generates an-swers based on all retrieved documents [35]. HippoRAG is a RAG framework inspired by humanlong-term memory that enables LLMs to continuously integrate knowledge across external docu-ments. In this paper, we also use ColBERTv2 [34] as its retriever [12]. IRCoT interleaves chain-of-thought (CoT) generation and knowledge retrieval steps in order to guide the retrieval by CoT andvice-versa. This interleaving allows retrieving more relevant information for later reasoning steps.It is a key technology for implementing multi-step retrieval in the existing RAG framework.

# 3.2 Experimental Results

# 3.2.1 Overall Results

The end-to-end Q&A performance is shown in Table 8. Within the RAG frameworks leveragingChatGPT-3.5 as backbone model, HippoRAG demonstrates superior performance compared to Na-tiveRAG. HippoRAG employs a human long-term memory strategy that facilitates the continuousintegration of knowledge from external documents into LLMs, thereby significantly enhancing Q&Acapabilities. However, given the substantial economic costs associated with utilizing ChatGPT-3.5,we opted to use the DeepSeek-V2 API as a viable alternative. On average, the performance of the IR-CoT + HippoRAG configuration utilizing the DeepSeek-V2 API slightly surpasses that of ChatGPT-

3.5. Our constructed framework KAG shows significant performance improvement compared toIRCoT $^ +$ HippoRAG, with EM increases of $1 1 . 5 \%$ , $1 9 . 8 \%$ , and $1 0 . 5 \%$ on HotpotQA, 2WikiMul-tiHopQA, and MuSiQue respectively, and F1 improvements of $12 . 5 \%$ , $1 9 . 1 \%$ , and $12 . 2 \%$ . Theseadvancements in end-to-end performance can largely be attributed to the development of more effec-tive indexing, knowledge alignment and hybrid solving libraries within our framework. We evaluatethe effectiveness of the single-step retriever and multi-step retriever, with the retrieval performanceshown in Table 9. From the experimental results, it is evident that the multi-step retriever generallyoutperforms the single-step retriever. Analysis reveals that the content retrieved by the single-stepretriever exhibits very high similarity, resulting in an inability to use the single-step retrieval out-comes to derive answers for certain data that require reasoning. The multi-step retriever alleviatesthis issue. Our proposed KAG framework directly utilizes the multi-step retriever and significantlyenhances retrieval performance through strategies such as mutual-indexing, logical form solving,and knowledge alignment.

<table><tr><td rowspan="2">Framework</td><td rowspan="2">Model</td><td colspan="2">HotpotQA</td><td colspan="2">2WikiMultiHopQA</td><td colspan="2">MuSiQue</td></tr><tr><td>EM</td><td>F1</td><td>EM</td><td>F1</td><td>EM</td><td>F1</td></tr><tr><td>NativeRAG [35, 34]</td><td>ChatGPT-3.5</td><td>43.4</td><td>57.7</td><td>33.4</td><td>43.3</td><td>15.5</td><td>26.4</td></tr><tr><td>HippoRAG [12, 34]</td><td>ChatGPT-3.5</td><td>41.8</td><td>55.0</td><td>46.6</td><td>59.2</td><td>19.2</td><td>29.8</td></tr><tr><td>IRCoT+NativeRAG</td><td>ChatGPT-3.5</td><td>45.5</td><td>58.4</td><td>35.4</td><td>45.1</td><td>19.1</td><td>30.5</td></tr><tr><td>IRCoT+HippoRAG</td><td>ChatGPT-3.5</td><td>45.7</td><td>59.2</td><td>47.7</td><td>62.7</td><td>21.9</td><td>33.3</td></tr><tr><td>IRCoT+HippoRAG</td><td>DeepSeek-V2</td><td>51.0</td><td>63.7</td><td>48.0</td><td>57.1</td><td>26.2</td><td>36.5</td></tr><tr><td>KAG w/ LFSref3</td><td>DeepSeek-V2</td><td>59.8</td><td>74.0</td><td>66.3</td><td>76.1</td><td>35.4</td><td>48.2</td></tr><tr><td>KAG w/ LFSHref3</td><td>DeepSeek-V2</td><td>62.5</td><td>76.2</td><td>67.8</td><td>76.2</td><td>36.7</td><td>48.7</td></tr></table>

Table 8: The end-to-end generation performance of different RAG models on three multi-hop Q&Adatasets. The values in bold and underline are the best and second best indicators respectively.

<table><tr><td rowspan="2"></td><td rowspan="2">Retriever</td><td colspan="2">HotpotQA</td><td colspan="2">2Wiki</td><td colspan="2">MuSiQue</td></tr><tr><td>Recall@2</td><td>Recall@5</td><td>Recall@2</td><td>Recall@5</td><td>Recall@2</td><td>Recall@5</td></tr><tr><td rowspan="7">Single-step</td><td>BM25 [36]</td><td>55.4</td><td>72.2</td><td>51.8</td><td>61.9</td><td>32.3</td><td>41.2</td></tr><tr><td>Contriever [37]</td><td>57.2</td><td>75.5</td><td>46.6</td><td>57.5</td><td>34.8</td><td>46.6</td></tr><tr><td>GTR [38]</td><td>59.4</td><td>73.3</td><td>60.2</td><td>67.9</td><td>37.4</td><td>49.1</td></tr><tr><td>RAPTOR [39]</td><td>58.1</td><td>71.2</td><td>46.3</td><td>53.8</td><td>35.7</td><td>45.3</td></tr><tr><td>Proposition [40]</td><td>58.7</td><td>71.1</td><td>56.4</td><td>63.1</td><td>37.6</td><td>49.3</td></tr><tr><td>NativeRAG [35, 34]</td><td>64.7</td><td>79.3</td><td>59.2</td><td>68.2</td><td>37.9</td><td>49.2</td></tr><tr><td>HippoRAG [12, 34]</td><td>60.5</td><td>77.7</td><td>70.7</td><td>89.1</td><td>40.9</td><td>51.9</td></tr><tr><td rowspan="5">Multi-step</td><td>IRCoT + BM25</td><td>65.6</td><td>79.0</td><td>61.2</td><td>75.6</td><td>34.2</td><td>44.7</td></tr><tr><td>IRCoT + Contriever</td><td>65.9</td><td>81.6</td><td>51.6</td><td>63.8</td><td>39.1</td><td>52.2</td></tr><tr><td>IRCoT + NativeRAG</td><td>67.9</td><td>82.0</td><td>64.1</td><td>74.4</td><td>41.7</td><td>53.7</td></tr><tr><td>IRCoT + HippoRAG</td><td>67.0</td><td>83.0</td><td>75.8</td><td>93.9</td><td>45.3</td><td>57.6</td></tr><tr><td>KAG</td><td>72.8</td><td>88.8</td><td>65.4</td><td>91.9</td><td>48.5</td><td>65.7</td></tr></table>

Table 9: The performance of different retrieval models on three multi-hop Q&A datasets

# 3.3 Ablation Studies

The objective of this experiment is to deeply investigate the impact of the knowledge alignment andlogic form solver on the final results. We conduct ablation studies for each module by substitutingdifferent methods and analyzing the changes in outcomes.

# 3.3.1 Knowledge Graph Indexing Ablation

In the graph indexing phase, we propose the following two substitution methods:

1) Mutual Indexing Method. As a baseline method of KAG, according to the introduction inSections 2.1 and 2.2, we use information extraction methods (such as OpenIE) to extract phrasesand triples in document chunks, and form the mutual-indexing between graph structure and text

chunks according to the hierarchical representation of LLMFriSPG, and then write them into KGstorage. We denote this method as M_Indexing.

2) Knowledge Alignment Enhancement. This method uses knowledge alignment to enhance theKG mutual-indexing and the logical form-guided reasoning & retrieval. According to the introduc-tion in Section 2.4, it mainly completes tasks such as the classification of instances and concepts,the prediction of hypernyms/hyponyms of concepts, the completion of the semantic relationshipsbetween concepts, the disambiguation and fusion of entities, etc., which enhances the semanticdistinction of knowledge and the connectivity between instances, laying a solid foundation for sub-sequent reasoning and retrieval guided by logical forms. We denote this method as K_Alignment.

# 3.3.2 Reasoning and Retrieval Ablation

Multi-round Reflection. We adopted the multi-round reflection mechanism from ReSP[26] toassess whether the Logical Form Solver has fully answered the question. If not, supplementaryquestions are generated for iterative solving until the information in global memory is sufficient.We analyzed the impact of the maximum iteration count n on the results, denoted as $r e f _ { n }$ . If $n = 1$ ,it means that the reflection mechanism is not enabled. In the reasoning and retrieval phase, wedesign the following three substitution methods:

1) Chunks Retriever. We define KAG’s baseline retrieval strategy with reference toHippoRAG’s[12] retrieval capabilities, with the goal of recalling the top_k chunks that support an-swering the current question. The Chunk score is calculated by weighting the vector similarity andthe personalized pagerank score. We denote this method as ChunkRetri, we denote ChunkRetri withn-round reflections as CRre fn . $C R _ { r e f _ { n } }$

2) Logical Form Solver (Enable Graph Retrieval). Next, we employ a Logical Form Solver forreasoning. This method uses pre-defined logical forms to parse and answer questions. First, itexplores the reasoning ability of the KG structure in $K G _ { c s }$ and $K G _ { f r }$ spaces, focusing on accuracyand rigor in reasoning. Then, it uses supporting_chunks in $R C$ to supplement retrieval when theprevious step of reasoning has no results. We denote this method as $L F S _ { r e f _ { n } }$ . The parameter $n$ ismaximum number of iteration parameter.

3) Logical Form Solver (Enable Hybrid Retrieval). In order to make full use of the mutual-indexing structure between $K G _ { f r }$ and $R C$ to further explore the role of KG structure in enhancingchunk retrieval, we modify the $L F S _ { r e f _ { n } }$ by disabling the Graph Retrieval functionality for directreasoning. Instead, all answers are generated using the Hybrid Retrieval method. This approachenables us to evaluate the contribution of graph retrieval to the performance of reasoning. We denotethis method as LF SHre fn . $L F S H _ { r e f _ { n } }$

Through the design of this ablation study, we aim to comprehensively and deeply understand theimpact of different graph indexing and reasoning methods on the final outcomes, providing strongsupport for subsequent optimization and improvement.

3.3.3 Experimental Results and Discussion

<table><tr><td rowspan="2">Graph Index</td><td rowspan="2">Reasoning</td><td colspan="2">HotpotQA</td><td colspan="2">2Wiki</td><td colspan="2">MuSiQue</td></tr><tr><td>EM</td><td>F1</td><td>EM</td><td>F1</td><td>EM</td><td>F1</td></tr><tr><td>M_Indexing</td><td>CRref3</td><td>52.4</td><td>65.4</td><td>48.2</td><td>56.0</td><td>24.6</td><td>36.6</td></tr><tr><td rowspan="5">K_Alignment</td><td>CRref3</td><td>54.7</td><td>69.5</td><td>62.7</td><td>72.5</td><td>29.6</td><td>41.1</td></tr><tr><td>LFSref1</td><td>59.1</td><td>73.4</td><td>65.2</td><td>74.4</td><td>31.3</td><td>43.4</td></tr><tr><td>LFSref3</td><td>59.8</td><td>74.0</td><td>66.3</td><td>76.1</td><td>35.4</td><td>48.2</td></tr><tr><td>LFSHref1</td><td>61.5</td><td>76.0</td><td>66.0</td><td>75.0</td><td>33.5</td><td>44.3</td></tr><tr><td>LFSHref3</td><td>62.5</td><td>76.2</td><td>67.8</td><td>76.2</td><td>36.7</td><td>48.7</td></tr></table>

Table 10: The end-to-end generation performance of different model methods on three multi-hopQ&A datasets. The backbone model is DeepSeek-V2 API. As is described in Algorithm 17, re f3represents a maximum of 3 rounds of reflection, and re f1 represents a maximum of 1 round, whichmeans that no reflection is introduced.

<table><tr><td rowspan="2">Graph Index</td><td rowspan="2">Reasoning</td><td colspan="2">HotpotQA</td><td colspan="2">2Wiki</td><td colspan="2">MuSiQue</td></tr><tr><td>R@2</td><td>R@5</td><td>R@2</td><td>R@5</td><td>R@2</td><td>R@5</td></tr><tr><td>M_Indexing</td><td>CRref3</td><td>61.5</td><td>73.8</td><td>54.6</td><td>59.7</td><td>39.3</td><td>52.8</td></tr><tr><td rowspan="5">K_Alignment</td><td>CRref3</td><td>56.3</td><td>83.0</td><td>66.3</td><td>88.1</td><td>40.0</td><td>62.3</td></tr><tr><td>LFSref1</td><td>/</td><td>/</td><td>/</td><td>/</td><td>/</td><td>/</td></tr><tr><td>LFSref3</td><td>/</td><td>/</td><td>/</td><td>/</td><td>/</td><td>/</td></tr><tr><td>LFSHref1</td><td>55.1</td><td>85.0</td><td>65.9</td><td>92.4</td><td>36.1</td><td>58.4</td></tr><tr><td>LFSHref3</td><td>72.7</td><td>88.8</td><td>65.4</td><td>91.9</td><td>48.4</td><td>65.6</td></tr></table>

Table 11: The recall performance of different methods across three datasets is presented. The an-swers to some sub-questions in the $L F S _ { r e f _ { n } }$ method use KG reasoning without recalling supportingchunks, which is not comparable to other methods in terms of recall rate. BackBone model isDeepSeek-V2 API.

![](images/472c3ee2800ad040924657d1121e30c87a56d9aa3fb2684ef9f04048bce807aa.jpg)

Figure 8: Each of the three test datasets comprises 1000 test problems, with 20 tasks processedconcurrently and maximum number of iterations $n$ is 3. $C R _ { r e f _ { 3 } }$ method exhibits the fastest execution,whereas $L F S H _ { r e f _ { 3 } }$ method is the slowest. Specifically, $C R _ { r e f _ { 3 } }$ method outperforms $L F S H _ { r e f _ { 3 } }$ methodby $149 \%$ , $101 \%$ 3 , and $134 \%$ 3 3 across the three datasets. In comparison, on the same dataset, the $L F S _ { r e f _ { 3 } }$method outperforms the $L F S H _ { r e f _ { 3 } }$ method by $13 \%$ , $22 \%$ , and $18 \%$ , respectively, with F1 relativelosses of $2 . 6 \%$ , $0 . 1 \%$ , and $1 . 0 \%$ , respectively.

![](images/90307c99a52d56575911ec804793614702fd2d0fcac0ce90d230fce1c7b1cd59.jpg)

![](images/06005b8c4f9bdc919a7eb85f40a9053c1ed3072dd2eaa8ad49823822c2dd62ff.jpg)

![](images/11a78f19cc90bd890d4b6d54f03bcbcb6eacab999e499c270446b65d5b306a80.jpg)

Figure 9: The connectivity of the graph exhibits a notable rightward shift after applyingK_Alignment,the distribution changes of 1-hop, 2-hop, and 3-hop neighbors are shown.

The analysis of the experimental outcomes can be approached from the following two perspectives:

1) Knowledge Graph Indexing. As is shown in Table 11, after incorporation Knowledge Align-ment into the KG mutual-indexing, the top-5 recall rates of $C R _ { r e f _ { 3 } }$ improved by $9 . 2 \%$ , $2 8 . 4 \%$ , and$9 . 5 \%$ respectively, with an average improvement of $1 5 . 7 \%$ . As shown in Figure 9, after enhancingknowledge alignment, the relation density is significantly increased, and the frequency-outdegreegraph is shifted to the right as a whole

• The 1-hop graph exhibits a notable rightward shift, indicating that the addition of semanticstructuring has increased the number of neighbors for each node, thereby enhancing thegraph’s density.

• The 2-hop and 3-hop graphs display an uneven distribution, with sparse regions on the leftand denser regions on the right. When comparing before and after K_Alignment, it isevident that the vertices in each dataset have shifted rightward, with the left side becomingmore sparse. This suggests that nodes with fewer multi-hop neighbors have gained newneighbors, leading to this observed pattern.

This signifies that the newly added semantic relations effectively enhance graph connectivity,thereby improving document recall rates.

2) Graph Inference Analysis. In terms of recall, $L F S H _ { r e f _ { 3 } }$ achieves improvements over $C R _ { r e f _ { 3 } }$ un-der the same graph index, with increases in top-5 recall rates by $15 \%$ , $3 2 . 2 \%$ , and $1 2 . 7 \%$ , averagingan improvement of $1 9 . 9 \%$ . This enhancement can be attributed to two main factors:

• $L F S H _ { r e f _ { 3 } }$ decomposes queries into multiple executable steps, with each sub-query retriev-ing chunks individually. As shown in the time analysis in Figure 8, both $L F S H _ { r e f _ { 3 } }$ and$L F S _ { r e f _ { 3 } }$ consume more than twice the time of $L F S H _ { r e f _ { 3 } }$ , indicating that increased compu-tational time is a trade-off for improved recall rates.

• $L F S H _ { r e f _ { 3 } }$ not only retrieves chunks but also integrates SPO triples from execution intochunk computation. Compared to $L F S H _ { r e f _ { 3 } }$ , it retrieves additional query-related relation-ships.

Due to the subgraph-based query answering in $L F S _ { r e f _ { 3 } }$ , it cannot be compared directly in recall rateanalysis but can be examined using the F1 metric. In comparison to $L F S H _ { r e f _ { 3 } }$ , $L F S _ { r e f _ { 3 } }$ answeredquestions based on the retrieved subgraphs with proportions of $33 \%$ , $34 \%$ , and $18 \%$ ,respectively.$L F S _ { r e f _ { 3 } }$ shows a decrease in the F1 metric by $2 . 2 \%$ , $0 . 1 \%$ , and $0 . 5 \%$ , while the computation timereduces by $12 \%$ , $22 \%$ , and $18 \%$ .

The analysis of the cases with decreased performance reveals that errors or incomplete SPOs duringthe construction phase lead to incorrect sub-query answers, resulting in wrong final answers. Thiswill be detailed in the case study. The reduction in computation time is primarily due to the moreefficient retrieval of SPOs compared to document chunks.

In industrial applications, computation time is a crucial metric. Although $L F S _ { r e f _ { n } }$ may introducesome errors, these can be improved through graph correction and completion. It is noteworthy thatin the current experiments, the slight decrease in metrics has been traded off for reduced computationtime, which we consider a feasible direction for industrial implementation.

For analyze the impact of the maximum number of iterations parameter $n$ on the results, $L F S _ { r e f _ { 1 } }$compared to $L F S _ { r e f _ { 3 } }$ , the F1 scores decreased by $0 . 6 \%$ , $1 . 6 \%$ , and $4 . 8 \%$ , respectively. Based onthe experiments of $L F S _ { r e f _ { 3 } }$ , the proportions for an iteration count of 1 were analyzed to be $9 7 . 2 \%$ ,$9 4 . 8 \%$ , and $8 7 . 9 \%$ ; $L F S H _ { r e f _ { 1 } }$ compared to $L F S H _ { r e f _ { 3 } }$ , the F1 scores decreased by $0 . 2 \%$ , $1 . 2 \%$ , and$4 . 4 \%$ , respectively. Based on the experiments of $L F S H _ { r e f _ { 3 } }$ , the proportions for an iteration count of1 were analyzed to be $9 8 . 3 \%$ , $9 5 . 2 \%$ , and $8 4 . 1 \%$ ; showing a positive correlation with the F1 scorereduction. Table 13 provides a detailed analysis of the effect of iteration rounds on the solution ofthe final answer. Increasing the maximum number of iterations parameter facilitates the re-planningof existing information when $L F S _ { r e f _ { n } }$ is unable to complete the solution, thereby addressing someunsolvable case.

# 4 Applications

# 4.1 KAG for E-Goverment

We used the KAG framework and combined it with the Alipay E-government service scenario tobuild a Q&A application that supports answering users’ questions about service methods, requiredmaterials, service conditions, and service locations. To build the e-government Q&A application,we first collected 11,000 documents about government services, and based on the methods describedin section 2, implemented functional modules such as index building, logical-form-guided reasoningand solving, semantic enhancement, and conditional summary generation.

During the offline index construction phase, the semantic chunking strategy is used to segment gov-ernment service documents to obtain specific matters and their properties such as the administrativeregion, service process, required materials, service location, target audience, and the correspondingchunks.

In the reasoning and solving phase, a logical function is generated based on the given user questionand graph index structure, and the logical form is executed according to the steps of the logicalfunction. First, the index item of the administrative area where the user is located is accuratelylocated. Then, the item name, group of people, etc. are used for search. Finally, the correspondingchunk is found through the required materials or service process. specifically inquired by the user.

In the semantic enhancement phase, we added two semantic relations, synonymy and hypernymy,between items. A synonymous relation refers to items in two different regions with different namesbut the same meaning, such as renewal of social security card and application for lost social securitycard; a co-hypernymy relation refers to two items belonging to different subcategories under thesame major category of items, such as applying for housing provident fund loan for construction ofnew housing and applying for housing provident fund loan for construction and renovation of newhousing, the two items have a common hypernymy applying for housing provident fund loan.

We compared the effects of the two technical solutions, NaiveRAG and KAG, as shown in the tablebelow. It is evident that KAG shows significant improvements in both completeness and accuracycompared to NaiveRAG.

<table><tr><td>Methods</td><td>SampleNum</td><td>Precision</td><td>Recall</td></tr><tr><td>NaiveRAG</td><td>492</td><td>66.5</td><td>52.6</td></tr><tr><td>KAG</td><td>492</td><td>91.6</td><td>71.8</td></tr></table>

Table 12: Ablation Experiments of KAG in E-Goverment Q&A.

# 4.2 KAG for E-Health

We have developed a medical Q&A application based on the Alipay Health Manager scenario,which supports answering user’s questions regarding popular science about disease, symptom,vaccine, operation, examination and laboratory test, also interpretation of medical indicators, med-ical recommendation, medical insurance policy inquires, hospital inquires, and doctor informationinquires. We have sorted out authoritative medical document materials through a team of medicalexperts, and produced more than 1.8 million entities and more than 400,000 term sets, with a totalof more than 5 million relations. Based on this high-quality KG, we have also produced more than700 DSL3 rules for indicator calculations to answer the questions of indicator interpretation.

During the knowledge construction phase, a strongly constrained schema is used to achieveprecise structural definition of entities such as diseases, symptoms, medications, and medicalexaminations. This approach facilitates accurate answers to questions and generates accurateknowledge, while also ensuring the rigor of relations between entities. In the reasoning phase, thelogical form is generated based on the user’s query, and then translated to DSL form for the queryon KG. The query result is returned in the form of triples as the answer. The logical form not onlyindicates how to query the KG, but also contains the key structural information in the user’s query(such as city, gender, age, indicator value, etc.). When parsing the logical form for query in graph,

the DSL rules which produced by medical expert will also be triggered, and the conclusion willbe returned in the form of triples. For example, if a user asks about "blood pressure $I 6 0 "$ , it willtrigger the rules as:

1  $\nvdash$  Define (DiseaseSeverity/'Grade 1 Hypertension') {  
2 SystolicPressure  $>= 140$  OR DiastolicPressure  $>= 90$   
3 }  
4  
5  $\nvdash$  Define (DiseaseSeverity/'Grade 2 Hypertension') {  
6 SystolicPressure  $>= 160$  OR DiastolicPressure  $>= 100$   
7 }  
8  
9  $\nvdash$  Define (Disease/'Hypertension') {  
10 DiseaseSeverity/'Grade 1 Hypertension' OR DiseaseSeverity/'Grade 2 Hypertension'  
11 }

, which strictly follows the defination of $\mathcal { L }$ in LLMFriSPG, and the conclusion that the person mayhave hypertension will be obtained.

In the semantic enhancement phase, we utilize the term set to express the two semantic relationsof synonymy and hypernym of concepts. The hypernym supports the expression of multiple hyper-nyms. During knowledge construction and user Q&A phase, entities are aligned with medical terms.For example, in the concept of surgery type, the hypernym of deciduous tooth extraction and ante-rior tooth extraction is tooth extraction. When the user only asks questions about tooth extraction,all its hyponyms can be retrieved based on the term, and then the related entity information can beretrieved for answering. With the support of KAG, we achieved a recall rate of $6 0 . 6 7 \%$ and a pre-cision rate of $8 1 . 3 2 \%$ on the evaluation set which sampling online Q&A queries. In the end-to-endscenario, the accuracy of medical insurance policy inquires (Beijing, Shanghai, Hangzhou) reached$7 7 . 2 \%$ , and the accuracy rate of popular science intentions has exceeded $94 \%$ , and the accuracy rateof interpreting indicator intentions has exceeded $93 \%$ .

# 5 Related Works

# 5.1 DIKW Pyramid

Following the DIKW pyramid theories[41, 42, 43, 44], after data is processed and contextualised, itbecomes information, and by integrating information with experience, understanding, and expertise,we gain knowledge. We usually use information extraction technology to obtain information fromthe original text[45, 46, 47], and obtain knowledge from the information through linking, fusion,analysis, and learning technology[43, 48, 46]. Information and knowledge are a single entity hav-ing different forms. There are no unified language to represent data, information and knowledge,RDF/OWL[49] only provides binary representation in the form of triples, and LPG[21] lacks supportfor knowledge semantics and classification. $\operatorname { S P G } ^ { 4 } [ 5 0]$ supports knowledge hierarchy and classifi-cation representation, but lacks text context support that is friendly to large language models. Ourproposed LLMFriSPG supports hierarchical representation from data to information to knowledge,and also provides reverse context-enhanced mutual-indexing.

# 5.2 Vector Similarity-based RAG

The external knowledge base use the traditional search engine provides an effective method for up-dating the knowledge of LLMs, it retrievals supporting documents by calculating the text or vectorsimilarity[1, 4] between the query and document, and then answers questions using the in-contextlearning method of LLMs. In addition, this method faces great challenges in understanding long-distance knowledge associations between documents. Simple vector-based retrieval is not suitablefor multi-step reasoning or tracking logical links between different information fragments. To ad-dress these challenges, researchers have explored methods such as fine-grained document segmenta-tion, CoT[33], and interactive retrieval[26, 2]. Despite these optimizations, traditional query-chunkssimilarity methods still has difficulty in accurately focusing on the relations between key knowledgein complex questions, resulting in low information density and ineffective association of remoteknowledge. We will illustrate the logical-form-guided solving method.

# 5.3 Information Retrieval-based GraphRAG

This type of methods use information extraction techniques to build entity and relation associationsbetween different documents, which can better perceive the global information of all documents.Typical tasks in the knowledge construction phase include: graph information extraction and knowl-edge construction&enhancement. Methods like GraphRAG[51], ToG 2.0[9], HippoRAG[12] useOpenIE to extract graph-structure information like entities and relations, some of them exploit multi-hop associations between entities to improve the effectiveness of cross-document retrieval[9, 12],methods like DALK[7] use PubTator Central(PTC) annotation to reduce the noise problem of ope-nIE, some of them utilize entity disambiguation technology to enhance the consistency of graphinformation[12, 52]. GraphRAG[51] generates element-level and community-level summaries whenbuilding offline indexes, and it uses a QFS[53] method to first calculate the partial response ofeach summary to the query and then calculate the final response. This inherent characteristic ofGraphRAG’s hierarchical summarization makes it difficult to solve questions such as multi-hopQ&A and incremental updates of documents. KGs constructed by openIE contains a lot of noiseor irrelevant information[54, 55, 56]. According to the DIKW pyramid hierarchy, these methodsonly extract the information graph structure and make limited attempts to disambiguate entities inthe transformation of information into knowledge,but they do not address issues such as seman-tic directionality and logical sensitivity. This paper will introduce a method in KAG to enhanceinformation-to-knowledge conversion based on domain concept semantic graph alignment.

# 5.4 KG-based Question and Answering

Reasoning based on traditional KGs has good explainability and transparency, but is limited by thescale of the domain KG, the comprehensiveness of knowledge, the detailed knowledge coverage, andthe timeliness of updates[57]. n this paper, we introduce HybridReasoning to alleviate issues such asknowledge sparsity, inconsistent entity granularity, and high graph construction costs. The approachleverages KG retrieval and reasoning to enhance generation, rather than completely replacing RAG.

To achieve KG-enhanced generation, it is necessary to address KG-based knowledge retrieval andreasoning. One approach is knowledge edge retrieval (IR)[58], which narrows down the scope bylocating the most relevant entities, relations, or triples based on the question. Another approachis semantic parsing (SP)[59, 60], which converts the question from unstructured natural languagedescriptions into executable database query languages (such as SQL, SPARQL[61], DSL5, etc.), orfirst generates structured logical forms (such as S-expressions[62, 63]) and then converts them intoquery languages.

Although conversational QA over large-scale knowledge bases can be achieved without explicitsemantic parsing (e.g., HRED-KVM[64]), most work focuses on exploring context-aware semanticparsers[60, 65, 63].

Some papers use sequence-to-sequence models to directly generate query languages[66, 67]. Thesemethods are developed for a specific query language, and sometimes even for a specific dataset, lack-ing generality for supporting different types of structured data. Others use step-by-step query graphgeneration and search strategies for semantic parsing[68, 69, 70]. This method is prone to uncontrol-lable issues generated by LLM, making queries difficult and having poor interpretability. Methodslike ChatKBQA[63], CBR-KBQA[71] completely generate S-expressions and provide various en-hancements for the semantic parsing process. However, the structure of S-expressions is relativelycomplex, and integrating multi-hop questions makes it difficult for LLMs to understand and incon-venient for integrating KBQA and RAG for comprehensive retrieval. To address these issues, wepropose a multi-step decomposed logical form to express the multi-hop retrieval and reasoning pro-cess, breaking down complex queries into multiple sub-queries and providing corresponding logicalexpressions, thereby achieving integrated retrieval of SPO and chunks.

# 5.5 Bidirectional-enhancement of LLMs and KGs

LLM and KG are two typical neural and symbolic knowledge utilization methods. Since the pre-trained language model such as BERT [72], well-performed language models are used to help im-prove the tasks of KGs. The LLMs with strong generalization capability are especially believed to be

helpful in the life-cycle of KGs. There are a lot of works conducted to explore the potential of LLMsfor in-KG and out-of-KG tasks. For example, using LLMs to generate triples to complete triples isproved to be much cheaper than the traditional human-centric KG construction process, with accept-able accuracy for the popular entities [73]. In the past decade, methods for in-KG tasks are designedby learning from KG structures, such as structure embedding-based methods. The text informationsuch as names and descriptions of entities is not fully utilized due to the limited text understandingcapability of natural language processing methods until LLMs provide a way. Some works usingLLMs for text semantic understanding and reasoning of entities and relations in KG completion[74], rule learning [75], complex logic querying [76], etc. On the other way, KGs are also widelyused to improve the performance of LLMs. For example, using KGs as external resources to provideaccurate factual information, mitigating hallucination of LLMs during answer generation [9], gen-erating complex logical questions answering planning data to fine-tune the LLMs, improving LLMsplanning capability and finally improving its logical reasoning capability [77], using KGs to uncoverassociated knowledge that has changed due to editing for better knowledge editing of LLMs [78],etc. The bidirectional-enhancement of LLMs and KGs is widely explored and partially achieved.

# 6 Limitations

In this article, we have proven the adaptability of the KAG framework in Q&A scenarios in verticaland open domains. However, the currently developed version of OpenSPG-KAG 0.5 still has majorlimitations that need to be continuously overcome, such as:

Implementing our framework requires multiple LLM calls during the construction and solv-ing phases. A substantial number of intermediate tokens required to be generated during the plan-ning stage to facilitate the breakdown of sub-problems and symbolic representation, this leads tocomputational and economic overhead, as illustrated in Table 14, where the problem decomposi-tion not only outputs sub-problems but also logical functions, resulting in approximately twice asmany generated tokens compared to merely decomposing the sub-problems. Meanwhile, currently,all model invocations within the KAG framework, including entity recognition, relation extraction,relation recall, and standardization, rely on large models. This multitude of models significantlyincreases the overall runtime. In future domain-specific implementations, tasks like relation recall,entity recognition, and standardization could be substituted with smaller, domain-specific models toenhance operational efficiency.

The ability to decompose and plan for complex problems requires a high level of capability.Currently, this is implemented using LLMs, but planning for complex issues remains a significantchallenge. For instance, when the task is to compare who is older, the problem should be decom-posed into comparing who was born earlier. Directly asking for age is not appropriate, as they aredeceased, and "what is the age" refers to the age at death, which doesn’t indicate who is older. De-composing and planning complex problems necessitates ensuring the model’s accuracy, stability,and solvability in problem decomposition and planning. The current version of the KAG frameworkdoes not yet address optimizations in these areas. We will further explore how pre-training, SFT, andCOT strategies can improve the model’s adaptability to logical forms and its planning and reasoningcapabilities.

Question: Which film has the director who is older, God’S Gift To Women or Aldri AnnetEnn Bråk?

Q1: Which director directed the film God’S Gift To Women? A1: Michael Curtiz

Q2: Which director directed the film Aldri Annet Enn Bråk? A2: Edith Carlmar

Q3: What is the age of the director of God’S Gift To Women? A3: 74 years old. Michael

Curtiz (December 24, 1886 to April 11, 1962)...

Q4: What is the age of the director of Aldri Annet Enn Bråk? A4: 91 years old. Edith

Carlmar (Edith Mary Johanne Mathiesen) (15 November 1911 to 17 May 2003) ...

Q5: Compare the ages of the two directors to determine which one is older. A5: Edith

Carlmar is older. Actually, Michael Curtiz was born earlier.

OpenIE significantly lowers the threshold for building KGs, but it also obviously increasesthe technical challenges of knowledge alignment. Although the experiments in this article haveshown that the accuracy and connectivity of extracted knowledge can be improved through knowl-edge alignment. However, there are still more technical challenges waiting to be overcome, suchas optimizing the accuracy of multiple-knowledge(such as events, rules, pipeline, etc.) extraction

and the consistency of multiple rounds of extraction. In addition, schema-constraint knowledgeextraction based on the experience of domain experts is also a key way to obtain rigorous domainknowledge, although the labor cost is high. These two methods should be applied collaboratively tobetter balance the requirements of vertical scenarios for the rigor of complex decision-making andthe convenience of information retrieval. For instance, when extracting team members from multi-ple texts and asked about the total number of team members, a comprehensive extraction is crucialfor providing an accurate answer based on the structured search results. Incorrect extractions alsoimpair response accuracy.

# 7 Conclusion and Future Work

In order to build professional knowledge services in vertical domains, fully activate the capabilitiesand advantages of symbolic KGs and parameterized LLMs, and at the same time significantlyreduce the construction cost of domain KGs, we proposed the KAG framework and try toaccelerated its application in professional domains. In this article, we introduce in detail theknowledge accuracy, information completeness and logical rigorous are the key characteristicsthat professional knowledge services must have. At the same time, we also introduce innovationssuch as LLMs friendly knowledge representation, mutual-indexing of knowledge structure and textchunks, knowledge alignment by semantic reasoning, logic-form-guided hybrid reasoning&solvingand KAG model. Compared with the current most competitive SOTA method, KAG has achievedsignificant improvements on public data sets such as HotpotQA, 2wiki, musique. We have alsoconducted case verifications in E-goverment Q&A and E-Health Q&A scenarios of Alipay, furtherproving the adaptability of the KAG framework in professional domains.

In the future, there is still more work to be explored to continuously reduce the cost of KGconstruction and improve the interpretability and transparency of reasoning, such as multipleknowledge extraction, knowledge alignment based on OneGraph, domain knowledge injection,large-scale instruction synthesis, illusion suppression of knowledge logic constraints, etc.

This study does not encompass the enhancement of models for decomposing and planning complexproblems, which remains a significant area for future research. In future work, KAG can beemployed as a reward model to provide feedback and assess the model’s accuracy, stability, andsolvability through the execution of planning results, thereby enhancing the capabilities of planningmodels.

We will also work in depth with the community organization OpenKG to continue to tackle keytechnical issues in the collaboration between LLMs and KGs.

# 8 Acknowledgements

This work was completed by the AntGroup Knowledge Graph Team, in addition to the authors inthe list, other contributors include Yuxiao He, Deng Zhao, Xiaodong Yan, Dong Han, FanzhuangMeng, Yang Lv, Zhiying Yin, etc, thank you all for your continuous innovation attempts and hardwork. This work also received strong support from Professor Huajun Chen, Researcher Wen Zhangof Zhejiang University, and Professor Wenguang Chen of AntGroup Technology Research Institute,thank you all.

# References

[1] Yunfan Gao, Yun Xiong, Xinyu Gao, Kangxiang Jia, Jinliu Pan, Yuxi Bi, Yi Dai, Jiawei Sun,and Haofen Wang. Retrieval-augmented generation for large language models: A survey. arXivpreprint arXiv:2312.10997, 2023.

[2] Zhihong Shao, Yeyun Gong, Yelong Shen, Minlie Huang, Nan Duan, and Weizhu Chen. En-hancing retrieval-augmented large language models with iterative retrieval-generation synergy.In Houda Bouamor, Juan Pino, and Kalika Bali, editors, Findings of the Association for Com-

putational Linguistics: EMNLP 2023, Singapore, December 6-10, 2023, pages 9248–9274.Association for Computational Linguistics, 2023.

[3] Jiawei Chen, Hongyu Lin, Xianpei Han, and Le Sun. Benchmarking large language mod-els in retrieval-augmented generation. In Proceedings of the AAAI Conference on ArtificialIntelligence, volume 38, pages 17754–17762, 2024.

[4] Wenqi Fan, Yujuan Ding, Liangbo Ning, Shijie Wang, Hengyun Li, Dawei Yin, Tat-Seng Chua,and Qing Li. A survey on rag meeting llms: Towards retrieval-augmented large languagemodels. In Proceedings of the 30th ACM SIGKDD Conference on Knowledge Discovery andData Mining, pages 6491–6501, 2024.

[5] Wenhao Yu, Hongming Zhang, Xiaoman Pan, Kaixin Ma, Hongwei Wang, and Dong Yu.Chain-of-note: Enhancing robustness in retrieval-augmented language models. arXiv preprintarXiv:2311.09210, 2023.

[6] Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, StevenTruitt, and Jonathan Larson. From local to global: A graph rag approach to query-focusedsummarization, 2024.

[7] Dawei Li, Shu Yang, Zhen Tan, Jae Young Baik, Sunkwon Yun, Joseph Lee, Aaron Chacko,Bojian Hou, Duy Duong-Tran, Ying Ding, et al. Dalk: Dynamic co-augmentation of llmsand kg to answer alzheimer’s disease questions with scientific literature. arXiv preprintarXiv:2405.04819, 2024.

[8] Minki Kang, Jin Myung Kwak, Jinheon Baek, and Sung Ju Hwang. Knowledge graph-augmented language models for knowledge-grounded dialogue generation, 2023.

[9] Shengjie Ma, Chengjin Xu, Xuhui Jiang, Muzhi Li, Huaren Qu, and Jian Guo. Think-on-graph2.0: Deep and interpretable large language model reasoning with knowledge graph-guidedretrieval. arXiv preprint arXiv:2407.10805, 2024.

[10] Yuntong Hu, Zhihan Lei, Zheng Zhang, Bo Pan, Chen Ling, and Liang Zhao. Grag: Graphretrieval-augmented generation, 2024.

[11] Costas Mavromatis and George Karypis. Gnn-rag: Graph neural retrieval for large languagemodel reasoning, 2024.

[12] Bernal Jiménez Gutiérrez, Yiheng Shu, Yu Gu, Michihiro Yasunaga, and Yu Su. Hipporag:Neurobiologically inspired long-term memory for large language models. arXiv preprintarXiv:2405.14831, 2024.

[13] Heiko Paulheim. Knowledge graph refinement: A survey of approaches and evaluation meth-ods. Semantic Web, 8:489–508, 2016.

[14] Siwei Wu, Xiangqing Shen, and Rui Xia. Commonsense knowledge graph completion viacontrastive pretraining and node clustering, 2023.

[15] Yi-Hui Chen, Eric Jui-Lin Lu, and Kwan-Ho Cheng. Integrating multi-head convolutionalencoders with cross-attention for improved sparql query translation, 2024.

[16] Yu Gu, Vardaan Pahuja, Gong Cheng, and Yu Su. Knowledge base question answering: Asemantic parsing perspective, 2022.

[17] Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, and YuanCao. React: Synergizing reasoning and acting in language models, 2023.

[18] Xanh Ho, Anh-Khoa Duong Nguyen, Saku Sugawara, and Akiko Aizawa. ConstructingA multi-hop QA dataset for comprehensive evaluation of reasoning steps. In Donia Scott,Núria Bel, and Chengqing Zong, editors, Proceedings of the 28th International Conference onComputational Linguistics, COLING 2020, Barcelona, Spain (Online), December 8-13, 2020,pages 6609–6625. International Committee on Computational Linguistics, 2020.

[19] Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, and Ashish Sabharwal. Musique:Multihop questions via single-hop question composition. Trans. Assoc. Comput. Linguistics,10:539–554, 2022.

[20] Dirk Groeneveld, Tushar Khot, Mausam, and Ashish Sabharwal. A simple yet strong pipelinefor hotpotqa. In Bonnie Webber, Trevor Cohn, Yulan He, and Yang Liu, editors, Proceedingsof the 2020 Conference on Empirical Methods in Natural Language Processing, EMNLP 2020,Online, November 16-20, 2020, pages 8839–8845. Association for Computational Linguistics,2020.

[21] Chandan Sharma and Roopak Sinha. A schema-first formalism for labeled property graphdatabases: Enabling structured data loading and analytics. In Proceedings of the 6th ieee/acminternational conference on big data computing, applications and technologies, pages 71–80,2019.

[22] Denny Vrandeciˇ c and Markus Krötzsch. Wikidata: a free collaborative knowledgebase. ´ Com-munications of the ACM, 57(10):78–85, 2014.

[23] Hugo Liu and Push Singh. Conceptnet—a practical commonsense reasoning tool-kit. BTtechnology journal, 22(4):211–226, 2004.

[24] Siye Wu, Jian Xie, Jiangjie Chen, Tinghui Zhu, Kai Zhang, and Yanghua Xiao. Howeasily do irrelevant inputs skew the responses of large language models? arXiv preprintarXiv:2404.03302, 2024.

[25] Honghao Gui, Hongbin Ye, Lin Yuan, Ningyu Zhang, Mengshu Sun, Lei Liang, and Hua-jun Chen. Iepile: Unearthing large-scale schema-based information extraction corpus. arXivpreprint arXiv:2402.14710, 2024.

[26] Zhouyu Jiang, Mengshu Sun, Lei Liang, and Zhiqiang Zhang. Retrieve, summarize,plan: Advancing multi-hop question answering with an iterative approach. arXiv preprintarXiv:2407.13101, 2024.

[27] Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida, Carroll Wainwright, Pamela Mishkin,Chong Zhang, Sandhini Agarwal, Katarina Slama, Alex Ray, et al. Training language models tofollow instructions with human feedback. Advances in neural information processing systems,35:27730–27744, 2022.

[28] Daniel M Ziegler, Nisan Stiennon, Jeffrey Wu, Tom B Brown, Alec Radford, Dario Amodei,Paul Christiano, and Geoffrey Irving. Fine-tuning language models from human preferences.arXiv preprint arXiv:1909.08593, 2019.

[29] Xiongtao Cui and Jungang Han. Chinese medical question answer matching based on interac-tive sentence representation learning. volume abs/2011.13573, 2020.

[30] Anastasios Nentidis, Georgios Katsimpras, Eirini Vandorou, Anastasia Krithara, AntonioMiranda-Escalada, Luis Gasco, Martin Krallinger, and Georgios Paliouras. Overviewof BioASQ 2022: The tenth BioASQ challenge on large-scale biomedical semantic index-ing and question answering. In Lecture Notes in Computer Science, pages 337–361. SpringerInternational Publishing, 2022.

[31] Zhouyu Jiang, Ling Zhong, Mengshu Sun, Jun Xu, Rui Sun, Hui Cai, Shuhan Luo, andZhiqiang Zhang. Efficient knowledge infusion via KG-LLM alignment. In Lun-Wei Ku,Andre Martins, and Vivek Srikumar, editors, Findings of the Association for ComputationalLinguistics, ACL 2024, Bangkok, Thailand and virtual meeting, August 11-16, 2024, pages2986–2999. Association for Computational Linguistics, 2024.

[32] Jintian Zhang, Cheng Peng, Mengshu Sun, Xiang Chen, Lei Liang, Zhiqiang Zhang, Jun Zhou,Huajun Chen, and Ningyu Zhang. Onegen: Efficient one-pass unified generation and retrievalfor llms, 2024.

[33] Harsh Trivedi, Niranjan Balasubramanian, Tushar Khot, and Ashish Sabharwal. Interleav-ing retrieval with chain-of-thought reasoning for knowledge-intensive multi-step questions. InAnna Rogers, Jordan L. Boyd-Graber, and Naoaki Okazaki, editors, Proceedings of the 61stAnnual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers),ACL 2023, Toronto, Canada, July 9-14, 2023, pages 10014–10037. Association for Computa-tional Linguistics, 2023.

[34] Keshav Santhanam, Omar Khattab, Jon Saad-Falcon, Christopher Potts, and Matei Zaharia.Colbertv2: Effective and efficient retrieval via lightweight late interaction. In Marine Carpuat,Marie-Catherine de Marneffe, and Iván Vladimir Meza Ruíz, editors, Proceedings of the 2022Conference of the North American Chapter of the Association for Computational Linguistics:Human Language Technologies, NAACL 2022, Seattle, WA, United States, July 10-15, 2022,pages 3715–3734. Association for Computational Linguistics, 2022.

[35] Patrick S. H. Lewis, Ethan Perez, Aleksandra Piktus, Fabio Petroni, Vladimir Karpukhin, Na-man Goyal, Heinrich Küttler, Mike Lewis, Wen-tau Yih, Tim Rocktäschel, Sebastian Riedel,and Douwe Kiela. Retrieval-augmented generation for knowledge-intensive NLP tasks. In

Hugo Larochelle, Marc’Aurelio Ranzato, Raia Hadsell, Maria-Florina Balcan, and Hsuan-TienLin, editors, Advances in Neural Information Processing Systems 33: Annual Conference onNeural Information Processing Systems 2020, NeurIPS 2020, December 6-12, 2020, virtual,2020.

[36] Stephen E. Robertson and Steve Walker. Some simple effective approximations to the 2-poisson model for probabilistic weighted retrieval. In W. Bruce Croft and C. J. van Rijsbergen,editors, Proceedings of the 17th Annual International ACM-SIGIR Conference on Researchand Development in Information Retrieval. Dublin, Ireland, 3-6 July 1994 (Special Issue of theSIGIR Forum), pages 232–241. ACM/Springer, 1994.

[37] Gautier Izacard, Mathilde Caron, Lucas Hosseini, Sebastian Riedel, Piotr Bojanowski, ArmandJoulin, and Edouard Grave. Unsupervised dense information retrieval with contrastive learning.Trans. Mach. Learn. Res., 2022, 2022.

[38] Jianmo Ni, Chen Qu, Jing Lu, Zhuyun Dai, Gustavo Hernández Ábrego, Ji Ma, Vincent Y.Zhao, Yi Luan, Keith B. Hall, Ming-Wei Chang, and Yinfei Yang. Large dual encodersare generalizable retrievers. In Yoav Goldberg, Zornitsa Kozareva, and Yue Zhang, editors,Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing,EMNLP 2022, Abu Dhabi, United Arab Emirates, December 7-11, 2022, pages 9844–9855.Association for Computational Linguistics, 2022.

[39] Parth Sarthi, Salman Abdullah, Aditi Tuli, Shubh Khanna, Anna Goldie, and Christopher D.Manning. RAPTOR: recursive abstractive processing for tree-organized retrieval. In TheTwelfth International Conference on Learning Representations, ICLR 2024, Vienna, Austria,May 7-11, 2024. OpenReview.net, 2024.

[40] Tong Chen, Hongwei Wang, Sihao Chen, Wenhao Yu, Kaixin Ma, Xinran Zhao, HongmingZhang, and Dong Yu. Dense X retrieval: What retrieval granularity should we use? CoRR,abs/2312.06648, 2023.

[41] Russell L Ackoff. From data to wisdom. Journal of applied systems analysis, 16(1):3–9, 1989.

[42] Sasa Baskarada and Andy Koronios. Data, information, knowledge, wisdom (dikw): A semi-otic theoretical and empirical exploration of the hierarchy and its quality dimension. Aus-tralasian Journal of Information Systems, 18(1), 2013.

[43] Jose Claudio Terra and Terezinha Angeloni. Understanding the difference between informationmanagement and knowledge management. KM Advantage, pages 1–9, 2003.

[44] Jonathan Hey. The data, information, knowledge, wisdom chain: the metaphorical link. Inter-governmental Oceanographic Commission, 26(1):1–18, 2004.

[45] Sunita Sarawagi et al. Information extraction. Foundations and Trends® in Databases,1(3):261–377, 2008.

[46] Gerhard Weikum and Martin Theobald. From information to knowledge: harvesting enti-ties and relationships from web sources. In Proceedings of the twenty-ninth ACM SIGMOD-SIGACT-SIGART symposium on Principles of database systems, pages 65–76, 2010.

[47] Jakub Piskorski and Roman Yangarber. Information extraction: Past, present and future. Multi-source, multilingual information extraction and summarization, pages 23–49, 2013.

[48] Priti Srinivas Sajja and Rajendra Akerkar. Knowledge-based systems for development. Ad-vanced Knowledge Based Systems: Model, Applications & Research, 1:1–11, 2010.

[49] Dean Allemang and James Hendler. Semantic web for the working ontologist: effective mod-eling in RDFS and OWL. Elsevier, 2011.

[50] Peng Yi, Lei Liang, Yong Chen Da Zhang, Jinye Zhu, Xiangyu Liu, Kun Tang, Jialin Chen,Hao Lin, Leijie Qiu, and Jun Zhou. Kgfabric: A scalable knowledge graph warehouse forenterprise data interconnection.

[51] Darren Edge, Ha Trinh, Newman Cheng, Joshua Bradley, Alex Chao, Apurva Mody, StevenTruitt, and Jonathan Larson. From local to global: A graph rag approach to query-focusedsummarization. arXiv preprint arXiv:2404.16130, 2024.

[52] Bhaskarjit Sarmah, Benika Hall, Rohan Rao, Sunil Patel, Stefano Pasquali, and DhagashMehta. Hybridrag: Integrating knowledge graphs and vector retrieval augmented generationfor efficient information extraction. arXiv preprint arXiv:2408.04948, 2024.

[53] Hoa Trang Dang. Duc 2005: Evaluation of question-focused summarization systems. InProceedings of the Workshop on Task-Focused Summarization and Question Answering, pages48–55, 2006.

[54] Hongming Zhang, Xin Liu, Haojie Pan, Yangqiu Song, and Cane Wing-Ki Leung. Aser: Alarge-scale eventuality knowledge graph. In Proceedings of the web conference 2020, pages201–211, 2020.

[55] Zhen Bi, Jing Chen, Yinuo Jiang, Feiyu Xiong, Wei Guo, Huajun Chen, and Ningyu Zhang.Codekgc: Code language model for generative knowledge graph construction. ACM Transac-tions on Asian and Low-Resource Language Information Processing, 23(3):1–16, 2024.

[56] Tianqing Fang, Hongming Zhang, Weiqi Wang, Yangqiu Song, and Bin He. Discos: Bridgingthe gap between discourse knowledge and commonsense knowledge. In Proceedings of theWeb Conference 2021, pages 2648–2659, 2021.

[57] Ling Tian, Xue Zhou, Yan-Ping Wu, Wang-Tao Zhou, Jin-Hao Zhang, and Tian-Shu Zhang.Knowledge graph and knowledge reasoning: A systematic review. Journal of Electronic Sci-ence and Technology, 20(2):100159, 2022.

[58] Yiyu Yao, Yi Zeng, Ning Zhong, and Xiangji Huang. Knowledge retrieval (kr). InIEEE/WIC/ACM International Conference on Web Intelligence (WI’07), pages 729–735. IEEE,2007.

[59] Jonathan Berant, Andrew Chou, Roy Frostig, and Percy Liang. Semantic parsing on freebasefrom question-answer pairs. In Proceedings of the 2013 Conference on Empirical Methods inNatural Language Processing, pages 1533–1544, Seattle, Washington, USA, October 2013.Association for Computational Linguistics.

[60] Daya Guo, Duyu Tang, Nan Duan, Ming Zhou, and Jian Yin. Dialog-to-action: Conversationalquestion answering over a large-scale knowledge base. In Samy Bengio, Hanna M. Wallach,Hugo Larochelle, Kristen Grauman, Nicolò Cesa-Bianchi, and Roman Garnett, editors, Ad-vances in Neural Information Processing Systems 31: Annual Conference on Neural Informa-tion Processing Systems 2018, NeurIPS 2018, December 3-8, 2018, Montréal, Canada, pages2946–2955, 2018.

[61] Jorge Pérez, Marcelo Arenas, and Claudio Gutierrez. Semantics and complexity of sparql. InIsabel Cruz, Stefan Decker, Dean Allemang, Chris Preist, Daniel Schwabe, Peter Mika, MikeUschold, and Lora M. Aroyo, editors, The Semantic Web - ISWC 2006, pages 30–43, Berlin,Heidelberg, 2006. Springer Berlin Heidelberg.

[62] Yu Gu, Sue Kase, Michelle Vanni, Brian Sadler, Percy Liang, Xifeng Yan, and Yu Su. Beyondi.i.d.: Three levels of generalization for question answering on knowledge bases. In Proceed-ings of the Web Conference 2021, pages 3477–3488, New York, NY, USA, 2021. Associationfor Computing Machinery.

[63] Haoran Luo, Haihong E, Zichen Tang, Shiyao Peng, Yikai Guo, Wentai Zhang, Chenghao Ma,Guanting Dong, Meina Song, Wei Lin, Yifan Zhu, and Luu Anh Tuan. Chatkbqa: A generate-then-retrieve framework for knowledge base question answering with fine-tuned large languagemodels. In Findings of the Association for Computational Linguistics: ACL 2024. Associationfor Computational Linguistics, 2024.

[64] Endri Kacupaj, Joan Plepi, Kuldeep Singh, Harsh Thakkar, Jens Lehmann, and MariaMaleshkova. Conversational question answering over knowledge graphs with transformer andgraph attention networks. In Paola Merlo, Jörg Tiedemann, and Reut Tsarfaty, editors, Pro-ceedings of the 16th Conference of the European Chapter of the Association for ComputationalLinguistics: Main Volume, EACL 2021, Online, April 19 - 23, 2021, pages 850–862. Associa-tion for Computational Linguistics, 2021.

[65] Yunshi Lan and Jing Jiang. Modeling transitions of focal entities for conversational knowledgebase question answering. In Chengqing Zong, Fei Xia, Wenjie Li, and Roberto Navigli, editors,Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics andthe 11th International Joint Conference on Natural Language Processing, ACL/IJCNLP 2021,(Volume 1: Long Papers), Virtual Event, August 1-6, 2021, pages 3288–3297. Association forComputational Linguistics, 2021.

[66] Pavan Kapanipathi, Ibrahim Abdelaziz, Srinivas Ravishankar, Salim Roukos, Alexander G.Gray, Ramón Fernandez Astudillo, Maria Chang, et al. Leveraging abstract meaning represen-tation for knowledge base question answering. In Findings of the Association for Computa-tional Linguistics: ACL/IJCNLP 2021, Online Event, August 1-6, 2021, volume ACL/IJCNLP2021 of Findings of ACL, pages 3884–3894. Association for Computational Linguistics, 2021.

[67] Reham Omar, Ishika Dhall, Panos Kalnis, and Essam Mansour. A universal question-answering platform for knowledge graphs. Proceedings of the ACM on Management of Data,1(1):57:1–57:25, 2023.

[68] Farah Atif, Ola El Khatib, and Djellel Difallah. Beamqa: Multi-hop knowledge graph questionanswering with sequence-to-sequence prediction and beam search. In Proceedings of the 46thInternational ACM SIGIR Conference on Research and Development in Information Retrieval,pages 781–790, New York, NY, USA, 2023. Association for Computing Machinery.

[69] Jinhao Jiang, Kun Zhou, Zican Dong, Keming Ye, Xin Zhao, and Ji-Rong Wen. Structgpt: Ageneral framework for large language model to reason over structured data. In Houda Bouamor,Juan Pino, and Kalika Bali, editors, Proceedings of the 2023 Conference on Empirical Meth-ods in Natural Language Processing, EMNLP 2023, Singapore, December 6-10, 2023, pages9237–9251. Association for Computational Linguistics, 2023.

[70] Yu Gu, Xiang Deng, and Yu Su. Don’t generate, discriminate: A proposal for groundinglanguage models to real-world environments. In Proceedings of the 61st Annual Meeting ofthe Association for Computational Linguistics (Volume 1: Long Papers), pages 4928–4949,Toronto, Canada, July 2023. Association for Computational Linguistics.

[71] Rajarshi Das, Manzil Zaheer, Dung Thai, Ameya Godbole, Ethan Perez, Jay Yoon Lee, LizhenTan, Lazaros Polymenakos, and Andrew McCallum. Case-based reasoning for natural lan-guage queries over knowledge bases. In Proceedings of the 2021 Conference on EmpiricalMethods in Natural Language Processing, pages 9594–9611, Online and Punta Cana, Domini-can Republic, November 2021. Association for Computational Linguistics.

[72] Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova. BERT: pre-trainingof deep bidirectional transformers for language understanding. In Jill Burstein, Christy Do-ran, and Thamar Solorio, editors, Proceedings of the 2019 Conference of the North AmericanChapter of the Association for Computational Linguistics: Human Language Technologies,NAACL-HLT 2019, Minneapolis, MN, USA, June 2-7, 2019, Volume 1 (Long and Short Pa-pers), pages 4171–4186. Association for Computational Linguistics, 2019.

[73] Blerta Veseli, Simon Razniewski, Jan-Christoph Kalo, and Gerhard Weikum. Evaluating theknowledge base completion potential of GPT. In Houda Bouamor, Juan Pino, and Kalika Bali,editors, Findings of the Association for Computational Linguistics: EMNLP 2023, Singapore,December 6-10, 2023, pages 6432–6443. Association for Computational Linguistics, 2023.

[74] Yichi Zhang, Zhuo Chen, Wen Zhang, and Huajun Chen. Making large language modelsperform better in knowledge graph completion. ACM MM, 2024.

[75] Linhao Luo, Jiaxin Ju, Bo Xiong, Yuan-Fang Li, Gholamreza Haffari, and Shirui Pan. Cha-trule: Mining logical rules with large language models for knowledge graph reasoning. CoRR,abs/2309.01538, 2023.

[76] Nurendra Choudhary and Chandan K. Reddy. Complex logical reasoning over knowledgegraphs using large language models. CoRR, abs/2305.01157, 2023.

[77] Junjie Wang, Mingyang Chen, Binbin Hu, Dan Yang, Ziqi Liu, Yue Shen, Peng Wei, ZhiqiangZhang, Jinjie Gu, Jun Zhou, Jeff Z. Pan, Wen Zhang, and Huajun Chen. Learning to plan forretrieval-augmented large language models from knowledge graphs. CoRR, abs/2406.14282,2024.

[78] Mengqi Zhang, Xiaotian Ye, Qiang Liu, Pengjie Ren, Shu Wu, and Zhumin Chen. Knowledgegraph enhanced large language model editing. CoRR, abs/2402.13593, 2024.

# A Example of KAG Solver

<table><tr><td>Round One</td></tr><tr><td>Initial Question: How many times did the plague occur in the birth place of Concerto in C Major Op 3 6&#x27;s composer?</td></tr><tr><td>Step1: Who is the composer of Concerto in C Major Op 3 6?.</td></tr><tr><td>Logical Form: Retrieval(s=s1:Work[C Major Op 3 6],p=p1:composer,o=o1:Person)</td></tr><tr><td>Graph Retrieval: (antonio vivaldi, composed concerto in, c major op 3 6)</td></tr><tr><td>Hybrid Retrieval: not executed</td></tr><tr><td>A1: Antonio Vivaldi</td></tr><tr><td>Step2: What is the birthplace of this composer?</td></tr><tr><td>Logical Form: Retrieval(s=o1,p=p2:brithPlace,o=o2:Place)</td></tr><tr><td>Graph Retrieval: not found</td></tr><tr><td>Hybrid Retrieval:</td></tr><tr><td>doc1:Antonio Vivaldi composed a mandolin concerto (Concerto in C major Op.3 6) ...</td></tr><tr><td>doc2:Antonio Lucio Vivaldi (Italian: ... Born in Venice...)</td></tr><tr><td>...</td></tr><tr><td>A2: Venice</td></tr><tr><td>Step3: How many times did the plague occur in this birthplace?</td></tr><tr><td>Logical Form: Retrieval(s=o2,p=p3:plagueOccurrence,o=o3:Plague)</td></tr><tr><td>Graph Retrieval: not found</td></tr><tr><td>Hybrid Retrieval:</td></tr><tr><td>doc1:Antonio Vivaldi composed a mandolin concerto (Concerto in C major Op.3 6) ...</td></tr><tr><td>doc2:The Black Death, also known as the Great Plague.. in Europe from 1347 to 1351..</td></tr><tr><td>...</td></tr><tr><td>A3: I don&#x27;t know</td></tr><tr><td>Step4: Count the number of plague occurrences.</td></tr><tr><td>Logical Form: Count(o3)-&gt;numbers</td></tr><tr><td>Graph Retrieval: not found</td></tr><tr><td>Hybrid Retrieval: not found</td></tr><tr><td>A4: I don&#x27;t know</td></tr><tr><td>Round Two</td></tr><tr><td>Rewrite Question: What specific records or historical accounts detail the number of plague occurrences in Venice during the mid-14th century?</td></tr><tr><td>Step1: What specific records or historical accounts detail the number of plague occurrences in Venice during the mid-14th century?</td></tr><tr><td>Logical Form: Retrieval(s=s1:City[Venice],p=p3:plagueOccurrencesInMid14thCentury,o=o1:Times)</td></tr><tr><td>Graph Retrieval: not found</td></tr><tr><td>Hybrid Retrieval:</td></tr><tr><td>doc1:In 1466, perhaps 40,000 people died of the plague...Plague occurred in Venice 22 times between 1361 and 1528...</td></tr><tr><td>doc2:The Black Death, also known as the Great Plague...</td></tr><tr><td>...</td></tr><tr><td>A1: The plague occurred in Venice 22 times between 1361 and 1528. The 1576–77 plague killed 50,000, almost a third of the population.</td></tr><tr><td>Final Answer</td></tr><tr><td>Question: How many times did the plague occur in the birth place of Concerto in C Major Op 3 6&#x27;s composer?</td></tr><tr><td>Step1: What specific records or historical accounts detail the number of plague occurrences in Venice during the mid-14th century?</td></tr><tr><td>A: 22 times</td></tr></table>

Table 13: An example of using logical-from to guide question planning, reasoning, retrieval, andanswer generation, and using multiple rounds of reflection to rephrase questions.

# B Example of Logical form Reasoner

<table><tr><td>Numerical Reasoning</td></tr><tr><td>question: Which sports team for which Cristiano Ronaldo played in 2011 was founded last ?</td></tr><tr><td>Step1: Identify the Sports Teams Cristiano Ronaldo Played for in 2011 .</td></tr><tr><td>Logical Form: Retrieval(s=s1:Player[Cristiano Ronaldo], p=p1:playedFor, o=o1:SportsTeam, p.PlayedForInYear=2011)</td></tr><tr><td>Step2: Determine the Foundation Years of Each Identified Team.</td></tr><tr><td>Logical Form: Retrieval(s=o1, p=p2:foundationYear, o=o2:Year)</td></tr><tr><td>Step3: Which team was founded last?</td></tr><tr><td>Logical Form: Sort(set=o1, orderby=o2, direction=max, limit=1)</td></tr><tr><td>question: What is the sum of 30 + 6 and the age of the founder of Tesla in 2027 ?</td></tr><tr><td>Step1: What is the sum of 30 + 6 ?</td></tr><tr><td>Logical Form: math1 = Math(30+6)</td></tr><tr><td>Step2: Who is the founder of Tesla?</td></tr><tr><td>Logical Form: Retrieval(s=s2:Company[Tesla], p=p2:founder, o=o2)</td></tr><tr><td>Step3: In which year was the founder of Tesla born?</td></tr><tr><td>Logical Form: Retrieval(s=o2, p=p3:yearOfBirth, o=o3)</td></tr><tr><td>Step4: How old will the founder of Tesla be in the year 2027?</td></tr><tr><td>Logical Form: math4 = Math(2027-o3)</td></tr><tr><td>Step5: What is the sum of math1 and math4?</td></tr><tr><td>Logical Form: math5 = Math(math1+math4)</td></tr><tr><td>Logical Reasoning</td></tr><tr><td>question: Find a picture containing vegetables or fruits.</td></tr><tr><td>Step1: Find pictures containing vegetables.</td></tr><tr><td>Logical Form: Retrieval(s=s1:Image, p=p2:contains, o=o1:Vegetables)</td></tr><tr><td>Step2: Find pictures containing fruits.</td></tr><tr><td>Action2: Retrieval(s=s2:Image, p=p2:contains, o=o2:Fruits)</td></tr><tr><td>Step3: Output s1, s2.</td></tr><tr><td>Logical Form: Output(s1, s2)</td></tr><tr><td>question: Find a picture containing vegetables and fruits.</td></tr><tr><td>Step1: Find pictures containing vegetables.</td></tr><tr><td>Logical Form: Retrieval(s=s1:Image, p=p2:contains, o=o1:Vegetables)</td></tr><tr><td>Step2: Find pictures containing fruits.</td></tr><tr><td>Logical Form: Retrieval(s=s1, p=p2:contains, o=o2:Fruits)</td></tr><tr><td>Step3: Output s1.</td></tr><tr><td>Logical Form: Output(s1)</td></tr><tr><td>Semantic Deduce</td></tr><tr><td>question: Do I need to present the original ID card when applying for a passport?</td></tr><tr><td>Step1: What documents are required to apply for a passport?</td></tr><tr><td>Logical Form: Retrieval(s=s1:Event[apply for a passport], p=p1:supportChunks, o=o1:Chunk)</td></tr><tr><td>Step2: Does this set of documents include the original identity card?</td></tr><tr><td>Logical Form: Deduce(left=o1, right=the original identity card, op=entailment)</td></tr></table>

Table 14: The cases of reasoning with logical form
