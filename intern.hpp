#ifndef INTERN_HPP
#define INTERN_HPP

#include <climits>
#include <functional>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <utility>

namespace intern {

	//---- Hash Utilities ------------------------------------------------------
	//
	//	Hash(args...) -> std::size_t:
	//		This function uses std::hash to calculate a hash value for each
	//		arg you pass it. It requires at least one arg. If there are multiple
	//		args, it combines the hash values into one before returning it.
	//
	//	HashTuple(arg) -> std::size_t:
	//		This function unpacks a tuple and calls Hash() on its elements.
	//		The "tuple" can really be anything tuple-like. In other words, arg
	//		can be a std::pair or a std::array -- not just a std::tuple.
	//

	template<typename T, typename... Ts>
		constexpr auto Hash(const T& v, const Ts&... vs) -> std::size_t {
			if constexpr(sizeof...(Ts) == 0) {
				return std::hash<T>{}(v);
			}
			else {
				//	The algorithm used to combine hashes is based on the boost
				//	algorithm. The 32-bit "magic" number has, however, been
				//	extended to 64 bits where appropriate. Also note that the
				//	combining is applied in reverse order since it was easier
				//	to do so in a recursive function; not that it matters.
				constexpr std::size_t kMagic =
					sizeof(std::size_t) * CHAR_BIT > 32u ?
					0x9e3779b97f4a7c15 : 0x9e3779b9;
				auto h = Hash(vs...);
				return h ^ (Hash(v) + kMagic + (h << 6) + (h >> 2));
			}
		}

	namespace details {
		struct TupleHash {
			std::size_t mHash;
			template<typename... Args>
				constexpr TupleHash(const Args&... args):
					mHash{Hash(args...)} {}
		};
	}
	template<typename Tuple>
		constexpr auto HashTuple(const Tuple& tuple) {
			return std::make_from_tuple<details::TupleHash>(tuple).mHash;
		}

	//---- Internment ----------------------------------------------------------
	//
	//	MakeInterned<Cls,Tuple>(args...)
	//			-> std::shared_ptr<const Interned<Cls,Tuple>:
	//		Given a hashable and equality-comparable class (Cls), this function
	//		returns an interned shared pointer to an instance of it.

	template<class Cls, typename Tuple>
		class Interned: public Cls {
			template<class Cls2, typename Tuple2, typename... Args>
				friend auto MakeInterned(Args&&... args)
					-> std::shared_ptr<const Interned<Cls2,Tuple2>>;
			using TInternMap = std::unordered_map<
				const Interned*, std::weak_ptr<const Interned>
				>;
			using TInternMut = std::mutex;
			inline static TInternMap gInternMap;
			inline static TInternMut gInternMut;
		 public:
			using Cls::Cls;
			~Interned() {
					std::lock_guard<TInternMut> lg{gInternMut};
					gInternMap.erase(this);
				}
		};
	template<class Cls, typename Tuple=void, typename... Args>
		auto MakeInterned(Args&&... args)
			-> std::shared_ptr<const Interned<Cls,Tuple>>
		{
			using TInterned = Interned<Cls,Tuple>;
			using TMutex = typename TInterned::TInternMut;
			std::shared_ptr<const TInterned> p;
			TInterned val{std::forward<Args>(args)...};
			std::lock_guard<TMutex> lg{TInterned::gInternMut};
			auto& map = TInterned::gInternMap;
			auto it = map.find(&val);
			if(it == map.end()) {
				p = std::make_shared<const TInterned>(std::move(val));
				map.insert(it, std::make_pair(p.get(), p));
			}
			else {
				p = it->second.lock();
			}
			return std::move(p);
		}
}

namespace std {
	template<typename Cls, typename Tuple>
		struct hash<const intern::Interned<Cls,Tuple>*> {
			auto operator()(
				const intern::Interned<Cls,Tuple>* p)
					const noexcept -> std::size_t
				{
					return intern::HashTuple(static_cast<Tuple>(*p));
				}
		};
	template<typename Cls>
		struct hash<const intern::Interned<Cls,void>*> {
			auto operator()(
				const intern::Interned<Cls,void>* p)
					const noexcept -> std::size_t
				{
					return hash<Cls>{}(*p);
				}
		};
}

#endif
