from flask_restful import Resource, Api
from flask import Flask, app, request, jsonify
import os.path
import joblib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
import re
import gensim
from itertools import combinations
import traceback

save_path = "./uploads/"

result = {}

class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

class lda_api(Resource):

    def put(self):
        return {'alo alo': 'alo dino'}

    def get(self, id):

        from blog import mysql, MySQL

        cursor = mysql.connection.cursor()
        query = "select * from articles where id = %s"
        res = cursor.execute(query, (id, ))
        if (res > 0):
            article = cursor.fetchone()

            file_name = article["title"]
            completeName = os.path.join(save_path, file_name)
            f = open(completeName, "w", encoding = "utf-8")
            f.write(article["content"])
            f.close()
        else:
            raise("Bir hata oluştu")

        try:
            raw_documents = []
            snippets = []
            with open("./uploads/{}".format(article["title"]) ,"r", encoding = "utf-8") as fin:
                for line in fin.readlines():
                    text = line.strip()
                    raw_documents.append( text )
                    # keep a short snippet of up to 100 characters as a title for each article
                    snippets.append( text[0:min(len(text),100)] )       

            custom_stop_words = []
            with open( "stopwordsTR.txt", "r", encoding = "utf-8") as fin:
                for line in fin.readlines():
                    custom_stop_words.append( line.strip() )
            # note that we need to make it hashable

            # use a custom stopwords list, set the minimum term-document frequency to 20 
            vectorizer = CountVectorizer(stop_words = custom_stop_words, min_df = 20)
            A = vectorizer.fit_transform(raw_documents)

            terms = vectorizer.get_feature_names()

            joblib.dump((A,terms,snippets), "articles-raw.pkl") 

            # we can pass in the same preprocessing parameters
            vectorizer = TfidfVectorizer(stop_words=custom_stop_words, min_df = 20)
            A = vectorizer.fit_transform(raw_documents)

            # extract the resulting vocabulary
            terms = vectorizer.get_feature_names()

            joblib.dump((A,terms,snippets), "articles-tfidf.pkl") 

            #2. sayfa

            (A,terms,snippets) = joblib.load( "articles-raw.pkl" )
            #print( "Loaded %d X %d document-term matrix" % (A.shape[0], A.shape[1]) )

            k=15
            model = LatentDirichletAllocation(n_components=k, max_iter=50, learning_method='online', learning_offset=50.,random_state=0).fit(A)
            W = model.fit_transform( A )
            H = model.components_

            W.shape
            H.shape

            def get_descriptor( terms, H, topic_index, top ):
                # reverse sort the values to sort the indices
                top_indices = np.argsort( H[topic_index,:] )[::-1]
                # now get the terms corresponding to the top-ranked indices
                top_terms = []
                for term_index in top_indices[0:top]:
                    top_terms.append( terms[term_index] )
                return top_terms

            descriptors = []
            for topic_index in range(k):
                descriptors.append( get_descriptor( terms, H, topic_index, 10 ) )
                str_descriptor = ", ".join( descriptors[topic_index] )
                #print("Topic %02d: %s" % ( topic_index+1, str_descriptor ) )

            def get_top_snippets( all_snippets, W, topic_index, top ):
                # reverse sort the values to sort the indices
                top_indices = np.argsort( W[:,topic_index] )[::-1]
                # now get the snippets corresponding to the top-ranked indices
                top_snippets = []
                for doc_index in top_indices[0:top]:
                    top_snippets.append( all_snippets[doc_index] )
                return top_snippets

            topic_snippets = get_top_snippets( snippets, W, 0, 10 )

            topic_snippets = get_top_snippets( snippets, W, 1, 10 )

            joblib.dump((W,H,terms,snippets), "articles-model-lda-k%02d.pkl" % k) 

            (A,terms,snippets) = joblib.load( "articles-raw.pkl" )

            kmin, kmax = 4, 15

            topic_models = []
            # try each value of k
            for k in range(kmin,kmax+1):
                # run LDA
                model = LatentDirichletAllocation(n_components=k, max_iter=10, learning_method='online', learning_offset=50.,random_state=0).fit(A)
                W = model.fit_transform( A )
                H = model.components_    
                # store for later
                topic_models.append( (k,W,H) )


            raw_documents = []
            with open("./uploads/{}".format(article["title"]) ,"r",encoding="utf-8") as fin:
                for line in fin.readlines():
                    raw_documents.append( line.strip().lower() )

            custom_stop_words = []
            with open( "stopwordsTR.txt", "r", encoding="utf-8" ) as fin:
                for line in fin.readlines():
                    custom_stop_words.append( line.strip().lower() )
            # note that we need to make it hashable

            class TokenGenerator:
                def __init__( self, documents, stopwords ):
                    self.documents = documents
                    self.stopwords = stopwords
                    self.tokenizer = re.compile( r"(?u)\b\w\w+\b" )

                def __iter__( self ):
                    #print("Building Word2Vec model ...")
                    for doc in self.documents:
                        tokens = []
                        for tok in self.tokenizer.findall( doc ):
                            if tok in self.stopwords:
                                tokens.append( "<stopword>" )
                            elif len(tok) >= 2:
                                tokens.append( tok )
                        yield tokens

            docgen = TokenGenerator( raw_documents, custom_stop_words )
            # the model has 500 dimensions, the minimum document-term frequency is 20
            w2v_model = gensim.models.Word2Vec(docgen, vector_size=500, min_count=20, sg=1)

            w2v_model.save("w2v-model-lda.bin")

            def calculate_coherence( w2v_model, term_rankings ):
                overall_coherence = 0.0
                for topic_index in range(len(term_rankings)):
                    # check each pair of terms
                    pair_scores = []
                    for pair in combinations( term_rankings[topic_index], 2 ):
                        pair_scores.append( w2v_model.wv.similarity(pair[0], pair[1]) )
                    # get the mean for all pairs in this topic
                    topic_score = sum(pair_scores) / len(pair_scores)
                    overall_coherence += topic_score
                # get the mean score across all topics
                return overall_coherence / len(term_rankings)

            def get_descriptor( all_terms, H, topic_index, top ):
                # reverse sort the values to sort the indices
                top_indices = np.argsort( H[topic_index,:] )[::-1]
                # now get the terms corresponding to the top-ranked indices
                top_terms = []
                for term_index in top_indices[0:top]:
                    top_terms.append( all_terms[term_index] )
                return top_terms

            k_values = []
            coherences = []
            for (k,W,H) in topic_models:
                # Get all of the topic descriptors - the term_rankings, based on top 10 terms
                term_rankings = []
                for topic_index in range(k):
                    term_rankings.append( get_descriptor( terms, H, topic_index, 10 ) )
                # Now calculate the coherence based on our Word2vec model
                k_values.append( k )
                coherences.append( calculate_coherence( w2v_model, term_rankings ) )

            ymax = max(coherences)
            xpos = coherences.index(ymax)
            best_k = k_values[xpos]

            k = best_k
            # get the model that we generated earlier.
            W = topic_models[k-kmin][1]
            H = topic_models[k-kmin][2]

            for topic_index in range(k):
                descriptor = get_descriptor( terms, H, topic_index, 10 )
                str_descriptor = ", ".join( descriptor )
                result["Topic %02d" % (topic_index+1)] = "%s" % ( str_descriptor ) 
            
            return jsonify(result)

        except ValueError:
            err = traceback.format_exc()
            result["Hata: "] = "%s" % err
            return jsonify(result)




